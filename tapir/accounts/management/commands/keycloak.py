from __future__ import annotations

import json
import sys

from django.core.management import BaseCommand
from keycloak.exceptions import KeycloakError

from tapir.accounts.services.keycloak_client_factory import get_provisioner_client
from tapir.accounts.services.keycloak_config import (
    KeycloakConfigCheck,
    build_keycloak_config_summary,
    check_keycloak_config,
)
from tapir.accounts.services.keycloak_desired_state import build_desired_state
from tapir.accounts.services.keycloak_reconciler import (
    KeycloakReconciler,
    KeycloakSetupError,
    ReconcileResult,
)


class Command(BaseCommand):
    help = (
        "Checks or synchronizes the Keycloak realm settings Tapir needs "
        "(clients, realm roles, the superuser group and service accounts). "
        "The target is configured with KEYCLOAK_ADMIN_SERVER_URL, "
        "KEYCLOAK_REALM_NAME and the provisioner client settings."
    )

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        check = subparsers.add_parser(
            "check", help="Read-only check for drift, exits 1 on drift"
        )
        check.add_argument("--json", action="store_true", help="Print JSON only")

        sync = subparsers.add_parser(
            "sync", help="Create or fix missing Keycloak settings"
        )
        sync.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would change",
        )
        sync.add_argument("--json", action="store_true", help="Print JSON only")

    def handle(self, *args, **options):
        action = options["action"]
        as_json = options.get("json", False)
        dry_run = action == "check" or options.get("dry_run", False)
        config = build_keycloak_config_summary()
        config_check = check_keycloak_config()

        if config_check.has_errors:
            self._fail_config(config_check, config, as_json)

        try:
            desired = build_desired_state()
            client = get_provisioner_client()
            reconciler = KeycloakReconciler(client, desired)
            result = reconciler.reconcile(dry_run=dry_run)

            if not dry_run:
                verification = reconciler.reconcile(dry_run=True)
                result.changes.extend(verification.changes)
                result.warnings.extend(verification.warnings)
                result.role_present = verification.role_present
                result.role_count = verification.role_count
                result.group_role_present = verification.group_role_present
                result.group_role_count = verification.group_role_count
        except (KeycloakSetupError, ValueError, KeycloakError) as error:
            if as_json:
                self.stdout.write(
                    json.dumps(
                        {"ok": False, "error": str(error), "config": config},
                        indent=2,
                    )
                )
            else:
                self.stderr.write(self.style.ERROR(str(error)))
            sys.exit(2)

        result.warnings = list(
            dict.fromkeys(
                result.warnings + [issue.format() for issue in config_check.warnings]
            )
        )

        if as_json:
            self.stdout.write(
                json.dumps(self._as_dict(result, config), indent=2, sort_keys=True)
            )
        else:
            self._print_result(result, action, dry_run, config)

        if result.has_errors:
            sys.exit(1)

    def _fail_config(
        self,
        config_check: KeycloakConfigCheck,
        config: dict,
        as_json: bool,
    ) -> None:
        message = "Invalid Keycloak configuration:\n" + "\n".join(
            issue.format() for issue in config_check.errors
        )
        if as_json:
            self.stdout.write(
                json.dumps(
                    {
                        "ok": False,
                        "error": message,
                        "config": config,
                        "config_issues": [
                            {
                                "level": issue.level,
                                "variable": issue.variable,
                                "message": issue.message,
                            }
                            for issue in config_check.errors
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            self.stderr.write(self.style.ERROR(message))
        sys.exit(2)

    def _as_dict(self, result: ReconcileResult, config: dict) -> dict:
        return {
            "config": config,
            "realm": config["realm"],
            "server_url": config["server_url"],
            "ok": not result.has_errors,
            "roles": {
                "present": result.role_present,
                "total": result.role_count,
            },
            "superuser": {
                "assigned": result.group_role_present,
                "total": result.group_role_count,
            },
            "changes": [
                {
                    "level": change.level,
                    "section": change.section,
                    "message": change.message,
                    "fixable": change.fixable,
                    "fixed": change.fixed,
                }
                for change in result.changes
            ],
            "warnings": result.warnings
            + [
                change.message for change in result.changes if change.level == "warning"
            ],
        }

    def _print_result(
        self,
        result: ReconcileResult,
        action: str,
        dry_run: bool,
        config: dict,
    ) -> None:
        realm = config["realm"]
        server_url = config["server_url"]
        verb = "Checking" if action == "check" else "Synchronizing"
        suffix = " (dry run)" if dry_run and action == "sync" else ""
        self.stdout.write(f"{verb} Keycloak realm {realm!r} at {server_url}{suffix}")
        self.stdout.write(
            "  target: "
            f"public={config['public_url']}, site={config['site_url']}, "
            f"clients={config['client_id']}, {config['frontend_client_id']}, "
            f"{config['provisioner_client_id']}"
        )

        for change in result.changes:
            if change.level == "warning":
                style = self.style.WARNING
            elif change.fixed:
                style = self.style.SUCCESS
            else:
                style = self.style.ERROR
            marker = "fixed" if change.fixed else change.level
            self.stdout.write(style(f"  [{marker}] {change.section}: {change.message}"))

        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(f"  [warning] {warning}"))

        self.stdout.write(f"roles: {result.role_present}/{result.role_count} present")
        self.stdout.write(
            "superuser: " f"{result.group_role_present}/{result.group_role_count} roles"
        )

        if action == "sync" and not dry_run:
            if result.created_roles:
                self.stdout.write("created roles: " + ", ".join(result.created_roles))
            if result.assigned_roles:
                self.stdout.write("assigned roles: " + ", ".join(result.assigned_roles))
            if result.created_clients:
                self.stdout.write(
                    "created clients: " + ", ".join(result.created_clients)
                )

        if result.has_errors:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(result.errors)} problem(s) remain. "
                    "Run `manage.py keycloak sync` or follow the messages above."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Keycloak is in sync."))
