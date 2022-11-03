import datetime
import os

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

import ctf_gameserver.web.registration.models as registration_models

from ctf_gameserver.web.scoring.views import _get_status_descriptions
from ctf_gameserver.web.scoring.decorators import registration_closed_required, services_public_required
from ctf_gameserver.web.scoring import models as scoring_models
from ctf_gameserver.web.scoring import calculations as scoring_calculations
from ctf_gameserver.web.scoring import views as scoring_views

from . import calculations

# old scoreboard currently uses [] so database defined order
SCOREBOARD_SERVICE_ORDER = ['name']

# data per tick does not change so can use longer caching
@cache_page(90)
@services_public_required('json')
def round_json(_, tick=-1):
    tick = int(tick)
    true_tick = tick

    scoreboard_tick = calculations.get_scoreboard_tick()
    points_tick = calculations.get_points_tick()

    if tick > scoreboard_tick or tick < -1:
        raise PermissionDenied()

    tick = min(points_tick, tick)

    scores, attackers_victims = calculations.scores(true_tick) # handles scoreboard freeze internally
    statuses = scoring_calculations.team_statuses(true_tick - 3, true_tick, only_team_fields=['user_id'])
    # convert team-keys to team_id-keys
    statuses = {team.user_id: v for team, v in statuses.items()}

    services = scoring_models.ServiceGroup.objects.order_by(*SCOREBOARD_SERVICE_ORDER).only('name').all()
    service_ids = []
    services_json = []
    for service in services:
        service_ids.append(service.id)
        services_json.append({
            "name": service.name,
            "first_blood": [], # this is an array for multiple flag stores
            "attackers": attackers_victims[service.id]["attackers"],
            "victims": attackers_victims[service.id]["victims"],
        })

    firstbloods_by_service = {}
    firstbloods = calculations.get_firstbloods(tick)
    for firstblood in firstbloods:
        if firstblood.tick <= tick:
            firstbloods_by_service[firstblood.service_id] = firstblood.team_id

    flagstores = scoring_models.Service.objects.all()
    flagstore_to_service_group = {}
    for flagstore in flagstores:
        flagstore_to_service_group[flagstore.id] = flagstore.service_group.id

    for firstblood_service_id, firstblood_team_id in firstbloods_by_service.items():
        service_idx = service_ids.index(flagstore_to_service_group[firstblood_service_id])
        if "first_blood" in services_json[service_idx]:
            services_json[service_idx]["first_blood"].append(firstblood_team_id)
        else:
            services_json[service_idx]["first_blood"] = [firstblood_team_id]

    response = {
        'tick': true_tick,
        'scoreboard': [],
        'status-descriptions': _get_status_descriptions(),
        'services': services_json
    }

    if tick == -1:
        teams = registration_models.Team.active_not_nop_objects.values_list('net_number', flat=True)
        for rank, team in enumerate(teams, start=1):
            team_entry = {
                'rank': rank,
                'team_id': team,
                'services': [],
                'points':  0,
                'o':  0,
                'do': 0,
                'd':  0,
                'dd': 0,
                's':  0,
                'ds': 0,
            }

            for service in services:
                team_entry['services'].append({
                    'm': 'no results yet',
                    'c': -1,
                    'dc': [-1, -1, -1],
                    'o':  0,
                    'do': 0,
                    'd':  0,
                    'dd': 0,
                    's':  0,
                    'ds': 0,
                    'cap': 0,
                    'dcap': 0,
                    'st': 0,
                    'dst': 0,
                })

            response['scoreboard'].append(team_entry)

    for rank, (team_id, points) in enumerate(scores.items(), start=1):
        team_entry = {
            'rank': rank,
            'team_id': team_id,
            'services': [],
            'points':  points['total']['total_score'],
            'o':  points['total']['offense_score'],
            'do': points['total']['offense_delta'],
            'd':  points['total']['defense_score'],
            'dd': points['total']['defense_delta'],
            's':  points['total']['sla_score'],
            'ds': points['total']['sla_delta'],
        }

        for service in services:
            service_statuses = []
            for status_tick in range(true_tick - 3, true_tick + 1):
                try:
                    service_statuses.insert(0, statuses[team_id][status_tick][service.id][-1])
                except KeyError:
                    import traceback
                    traceback.print_exc()
                    service_statuses.insert(0, -1)

            try:
                flagstores = []
                srv_statuses = statuses[team_id][true_tick][service.id]
                msg = ''
                for i, key in enumerate(sorted(srv_statuses.keys())):
                    if key == -1:
                        continue
                    flagstores.append(srv_statuses[key])
                    fs_st, fs_msg = srv_statuses[key]
                    fs_st_str = scoring_views._get_status_descriptions()[fs_st]
                    if len(fs_msg) > 0:
                         fs_msg = f' - {fs_msg}'
                    msg += f'Flagstore {i} ({fs_st_str}){fs_msg}\n'
            except KeyError:
                import traceback
                traceback.print_exc()
                msg = 'status unknown'

            service_points = points['services'][service.id]
            team_entry['services'].append({
                'm': msg,
                'c': service_statuses[0],
                'dc': service_statuses[1:4],
                'o':  service_points['offense_score'],
                'do': service_points['offense_delta'],
                'd':  service_points['defense_score'],
                'dd': service_points['defense_delta'],
                's':  service_points['sla_score'],
                'ds': service_points['sla_delta'],
                'cap': service_points['flags_captured'],
                'dcap': service_points['flags_captured_delta'],
                'st': service_points['flags_lost'],
                'dst': service_points['flags_lost_delta'],
            })

        response['scoreboard'].append(team_entry)

    return JsonResponse(response)

# Short cache timeout only, because there is already caching going on in calculations
@cache_page(5)
@services_public_required('json')
def per_team_json(_, team=-1):
    team = int(team)

    # get service ids in scoreboard order
    service_ids = list(scoring_models.ServiceGroup.objects.order_by(*SCOREBOARD_SERVICE_ORDER).values_list('id', flat=True))

    team_scores = calculations.per_team_scores(team, service_ids)

    response = {
        'points': team_scores
    }

    return JsonResponse(response)

# every scoreboard UI will query this every 2-10 sec so better cache this
# but don't cache it too long to avoid long wait times after tick increment 
# it's not expensive anyway (two single row queries)
@cache_page(2)
@registration_closed_required
def current_json(_):
    game_control = scoring_models.GameControl.get_instance()
    current_tick = game_control.current_tick
    
    scoreboard_tick = calculations.get_scoreboard_tick()

    next_tick_start_offset = (current_tick + 1) * game_control.tick_duration
    current_tick_until = game_control.start + datetime.timedelta(seconds=next_tick_start_offset)
    unix_epoch = datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
    current_tick_until_unix = (current_tick_until-unix_epoch).total_seconds()

    state = int(not game_control.competition_started())

    if game_control.competition_frozen():
        state = 2
    if game_control.competition_over():
        state = 1

    result = {
        "state": state,
        "current_tick": current_tick,
        "current_tick_until": current_tick_until_unix,
        "scoreboard_tick": scoreboard_tick
    }
    return JsonResponse(result, json_dumps_params={'indent': 2})

@cache_page(60)
# This is essentially just a registered teams list so could be made public even earlier
@registration_closed_required
def teams_json(_):

    teams = registration_models.Team.active_not_nop_objects \
      .select_related('user') \
      .only('user__username', 'affiliation', 'country', 'image') \
      .order_by('user_id') \
      .all()

    ip_pattern = os.environ['CTF_IPPATTERN']

    result = {}
    for team in teams:
        team_json = {
            "name": team.user.username,
            "aff": team.affiliation,
            #"country": team.country,
            "vulnbox": ip_pattern % team.net_number,
            #"logo": None if not team.image else team.image.get_thumbnail_url()
            "logo": team.country
        }
        result[team.user_id] = team_json

    return JsonResponse(result, json_dumps_params={'indent': 2})
