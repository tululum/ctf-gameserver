INSERT INTO flatpages_flatpage (id, title, content, category_id, ordering, slug)
VALUES (1, '', 'Welcome to the ECSC 2022 Attack-Defense CTF', NULL, 10, '');

INSERT INTO scoring_gamecontrol
(
    id,
    competition_name,
    services_public,
    "start",
    "end",
    "freeze",
    tick_duration,
    valid_ticks,
    flag_prefix,
    current_tick,
    registration_open,
    registration_confirm_text,
    min_net_number,
    max_net_number
)
VALUES (
    1,
    '{{ competition_name }}',
    '{{ services_public }}',
    '{{ event_start }}',
    '{{ event_end }}',
    '{{ event_freeze }}',
    {{ tick_duration }},
    {{ valid_ticks }},
    '{{ flag_prefix }}',
    -1,
    false,
    '',
    NULL,
    NULL
);

UPDATE scoring_gamecontrol
SET competition_name='{{ competition_name }}',
    services_public='{{ services_public }}',
    "start"='{{ event_start }}',
    "end"='{{ event_end }}',
    "freeze"='{{ event_freeze }}',
    tick_duration={{ tick_duration }},
    valid_ticks={{ valid_ticks }},
    flag_prefix='{{ flag_prefix }}',
    registration_open=false,
    registration_confirm_text='',
    min_net_number=NULL,
    max_net_number=NULL
WHERE id=1;

{% for s in game_servicegroups %}
INSERT INTO scoring_servicegroup (id, name, slug)
VALUES ({{ s.id }}, '{{ s.name }}', '{{ s.slug }}');
{% endfor %}

{% for s in game_services %}
INSERT INTO scoring_service (id, name, slug, service_group_id)
VALUES ({{ s.id }}, '{{ s.name }}', '{{ s.slug }}', {{ s.group }});
{% endfor %}

{% for t in teams %}
INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
VALUES ({{ t.id }}, '{{ t.pass | my_pbkdf2_sha256 }}', NULL, {%
	if 'admin' in t and t.admin %}true{% else %}false{% endif %}, '{{ t.name | replace("\x27", "\x27\x27") }}', '', '', '{{ t.email }}', {%
	if 'admin' in t and t.admin %}true{% else %}false{% endif %}, true, now());

{% if 'admin' not in t %}
INSERT INTO registration_team (user_id, net_number, informal_email, image, affiliation, country, nop_team)
VALUES ({{ t.id }}, {{ t.id }}, '{{ t.email }}', '', '{{ t.aff | default('') }}', '{{ t.logo }}', {%
	if 'nop' in t and t.nop %}true{% else %}false{% endif %});
{% endif %}

{% endfor %}
