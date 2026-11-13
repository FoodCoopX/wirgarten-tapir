#!/bin/bash
# Keycloak administration on the command line for the Keycloak of docker-compose.yml.
#
#   scripts/tapir_kcadm.sh realms                                    list the realms
#   scripts/tapir_kcadm.sh user list [<search>]
#   scripts/tapir_kcadm.sh user show <mail>
#   scripts/tapir_kcadm.sh user add <mail> [--first <name>] [--last <name>] [--password <pw>] [--superuser]
#   scripts/tapir_kcadm.sh user passwd <mail> [--password <pw>] [--temporary]   generated if not given
#   scripts/tapir_kcadm.sh user role <mail> <role> [--remove]                   needs an admin, see below
#   scripts/tapir_kcadm.sh user group <mail> <group> [--remove]                 e.g. superuser
#   scripts/tapir_kcadm.sh user enable|disable|delete|logout <mail>
#   scripts/tapir_kcadm.sh roles | groups
#   scripts/tapir_kcadm.sh raw <kcadm.sh arguments>                             -r <realm> is added
#
# Also available as: make keycloak ARGS="user list"
#
# Settings (environment variables):
#   KC_REALM           realm of the commands, default "tapir"
#   KC_EXEC            how kcadm.sh is started in the Keycloak container, default
#                      "docker compose exec -T keycloak", e.g. "podman exec -i <container>"
#   KC_CLIENT_ID, KC_CLIENT_SECRET   login as this client of the realm, default "tapir-backend"
#                      with the secret of docker/keycloak/import/tapir-realm.json. This is the
#                      account Tapir itself uses. It may manage users, passwords and groups, but
#                      not list roles or give roles to a user.
#   KC_ADMIN_USER, KC_ADMIN_PASSWORD   login as an admin of the master realm instead. Needed for
#                      "roles" and "user role". The Keycloak of docker-compose.yml may not have
#                      such an admin, then create one first.
#
# This is for the Keycloak of the development setup. A Keycloak user only lets someone log in:
# the permissions of Tapir come from the realm roles and the group "superuser".
set -euo pipefail

REALM="${KC_REALM:-tapir}"
KC_CLIENT_ID="${KC_CLIENT_ID:-tapir-backend}"
KC_CLIENT_SECRET="${KC_CLIENT_SECRET:-**********}"
KC_ADMIN_USER="${KC_ADMIN_USER:-}"
KC_ADMIN_PASSWORD="${KC_ADMIN_PASSWORD:-}"
KC_EXEC="${KC_EXEC:-docker compose exec -T keycloak}"

die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
random_string() { tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$1" || true; }
usage() { sed -n '2,/^[^#]/{/^#/p}' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

case "${1:-}" in -h|--help|"") usage ;; esac

# The login is kept in a file inside the container, so it is repeated for every call. That is
# cheap and keeps the script free of state on the host.
# shellcheck disable=SC2086  # KC_EXEC is a command with arguments
kcadm() { $KC_EXEC /opt/keycloak/bin/kcadm.sh "$@" --config /tmp/kcadm.config; }
if [ -n "$KC_ADMIN_USER" ]; then
    kcadm config credentials --server http://localhost:8080 --realm master \
        --user "$KC_ADMIN_USER" --password "$KC_ADMIN_PASSWORD" >/dev/null 2>&1 \
        || die "login as admin $KC_ADMIN_USER failed (KC_EXEC=$KC_EXEC)"
else
    kcadm config credentials --server http://localhost:8080 --realm "$REALM" \
        --client "$KC_CLIENT_ID" --secret "$KC_CLIENT_SECRET" >/dev/null 2>&1 \
        || die "login as client $KC_CLIENT_ID in realm $REALM failed (is Keycloak running? is KC_EXEC right? KC_EXEC=$KC_EXEC)"
fi

# Roles need more rights than the client of Tapir has: say so instead of showing "403"
needs_admin() {
    local out
    out="$("$@" 2>&1)" && { [ -z "$out" ] || echo "$out"; return 0; }
    case "$out" in
        *403*) die "forbidden: the client $KC_CLIENT_ID may not do this, set KC_ADMIN_USER and KC_ADMIN_PASSWORD" ;;
        *) echo "$out" >&2; return 1 ;;
    esac
}

# "realms" is the only command that needs no realm
if [ "$1" = realms ]; then
    kcadm get realms --fields realm --format csv --noquotes 2>/dev/null | awk '$1 != "master"'
    exit 0
fi
kcadm get "realms/$REALM" --fields realm >/dev/null 2>&1 || die "realm '$REALM' not found (realms: $0 realms)"

user_id() {  # mail
    local id
    id="$(kcadm get users -r "$REALM" -q "email=$1" -q exact=true --fields id --format csv --noquotes | head -n 1)"
    [ -n "$id" ] || die "no user $1 in realm $REALM"
    echo "$id"
}

group_id() {  # name
    local id
    id="$(kcadm get groups -r "$REALM" -q "search=$1" -q exact=true --fields id --format csv --noquotes | head -n 1)"
    [ -n "$id" ] || die "no group $1 in realm $REALM"
    echo "$id"
}

set_password() {  # mail password temporary
    if [ "$3" = true ]; then
        kcadm set-password -r "$REALM" --username "$1" --new-password "$2" --temporary
    else
        kcadm set-password -r "$REALM" --username "$1" --new-password "$2"
    fi
}

cmd="${1:-}"; shift || true
case "$cmd" in
    user)
        sub="${1:-}"; shift || true
        case "$sub" in
            list)
                kcadm get users -r "$REALM" ${1:+-q "search=$1"} --limit 1000 \
                    --fields username,firstName,lastName,enabled,emailVerified --format csv --noquotes ;;
            show)
                id="$(user_id "${1:?mail}")"
                kcadm get "users/$id" -r "$REALM" --fields username,email,firstName,lastName,enabled,emailVerified,requiredActions
                echo "realm roles:"; kcadm get "users/$id/role-mappings/realm/composite" -r "$REALM" --fields name --format csv --noquotes | sed 's/^/  /'
                echo "groups:"; kcadm get "users/$id/groups" -r "$REALM" --fields name --format csv --noquotes | sed 's/^/  /' ;;
            add)
                mail="${1:?mail}"; shift
                first="" last="" password="" superuser=false
                while [ $# -gt 0 ]; do case "$1" in
                    --first) first="${2:?name}"; shift 2 ;; --last) last="${2:?name}"; shift 2 ;;
                    --password) password="${2:?password}"; shift 2 ;; --superuser) superuser=true; shift ;;
                    *) die "unknown option $1" ;; esac; done
                kcadm create users -r "$REALM" -s "username=$mail" -s "email=$mail" -s enabled=true \
                    -s emailVerified=true ${first:+-s "firstName=$first"} ${last:+-s "lastName=$last"} >/dev/null 2>&1 \
                    || die "could not create $mail (exists already?)"
                temporary=false
                [ -n "$password" ] || { password="$(random_string 16)"; temporary=true; }
                set_password "$mail" "$password" "$temporary"
                [ "$superuser" = true ] && kcadm update "users/$(user_id "$mail")/groups/$(group_id superuser)" -r "$REALM" -n
                echo "created $mail in $REALM"
                [ "$temporary" = true ] && echo "temporary password (must be changed at first login): $password"
                true ;;
            passwd)
                mail="${1:?mail}"; shift
                password="" temporary=false
                while [ $# -gt 0 ]; do case "$1" in
                    --password) password="${2:?password}"; shift 2 ;; --temporary) temporary=true; shift ;;
                    *) die "unknown option $1" ;; esac; done
                [ -n "$password" ] || { password="$(random_string 16)"; temporary=true; echo "new password: $password"; }
                set_password "$mail" "$password" "$temporary"
                echo "password of $mail set$([ "$temporary" = true ] && echo ' (temporary, must be changed at next login)')" ;;
            role)
                mail="${1:?mail}" role="${2:?role}"
                if [ "${3:-}" = --remove ]; then
                    needs_admin kcadm remove-roles -r "$REALM" --uusername "$mail" --rolename "$role"; echo "removed $role from $mail"
                else
                    needs_admin kcadm add-roles -r "$REALM" --uusername "$mail" --rolename "$role"; echo "added $role to $mail"
                fi ;;
            group)
                mail="${1:?mail}" group="${2:?group}"
                if [ "${3:-}" = --remove ]; then
                    kcadm delete "users/$(user_id "$mail")/groups/$(group_id "$group")" -r "$REALM"; echo "removed $mail from $group"
                else
                    kcadm update "users/$(user_id "$mail")/groups/$(group_id "$group")" -r "$REALM" -n; echo "added $mail to $group"
                fi ;;
            enable|disable)
                kcadm update "users/$(user_id "${1:?mail}")" -r "$REALM" -s "enabled=$([ "$sub" = enable ] && echo true || echo false)"
                echo "$1 ${sub}d" ;;
            delete)
                kcadm delete "users/$(user_id "${1:?mail}")" -r "$REALM"; echo "deleted $1 in Keycloak (the Tapir user is kept)" ;;
            logout)
                kcadm create "users/$(user_id "${1:?mail}")/logout" -r "$REALM" -b '{}'; echo "sessions of $1 ended" ;;
            *) usage 2 ;;
        esac ;;
    roles) needs_admin kcadm get roles -r "$REALM" --fields name,description --format csv --noquotes ;;
    groups) kcadm get groups -r "$REALM" --fields name --format csv --noquotes ;;
    raw) kcadm "$@" -r "$REALM" ;;
    *) usage 2 ;;
esac
