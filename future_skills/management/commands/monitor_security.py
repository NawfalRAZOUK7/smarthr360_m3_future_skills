"""
Security Event Monitor
======================

Django management command to monitor and analyze security events.
"""

import json
import os
import re
from collections import Counter
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Monitor and analyze security events from logs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Number of hours to analyze (default: 24)",
        )
        parser.add_argument(
            "--tail",
            type=int,
            default=1000,
            help="Number of log lines to read from end (default: 1000)",
        )
        parser.add_argument("--json", action="store_true", help="Output in JSON format")

    def handle(self, *args, **options):
        hours = options["hours"]
        tail = options["tail"]
        json_output = options["json"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== Security Event Analysis (Last {hours} hours) ===\n"
            )
        )

        # Find security log file
        log_file = "logs/security.log"
        if not os.path.exists(log_file):
            self.stdout.write(self.style.WARNING("No security log file found"))
            return

        # Parse log file
        events = self._parse_log_file(log_file, tail)

        # Analyze events
        analysis = self._analyze_events(events, hours)

        # Output results
        if json_output:
            self.stdout.write(json.dumps(analysis, indent=2))
        else:
            self._print_analysis(analysis)

    def _parse_log_file(self, log_file, tail_lines):
        """Parse security log file and extract events."""
        events = []

        try:
            # Read last N lines
            with open(log_file, "r") as f:
                lines = f.readlines()[-tail_lines:]

            for line in lines:
                # Try to parse JSON logs
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError:
                    # Try to parse text logs
                    event = self._parse_text_log(line)
                    if event:
                        events.append(event)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading log file: {e}"))

        return events

    def _parse_text_log(self, line):
        """Parse text format log line."""
        # Extract basic info from text logs
        match = re.match(r"\[(.*?)\] (.*?) (.*?): (.*)", line)
        if match:
            return {
                "levelname": match.group(1),
                "asctime": match.group(2),
                "name": match.group(3),
                "message": match.group(4),
            }
        return None

    def _analyze_events(self, events, hours):
        """Analyze security events."""
        cutoff_time = timezone.now() - timedelta(hours=hours)

        # Filter by time
        recent_events = [
            e for e in events if self._is_recent(e.get("asctime", ""), cutoff_time)
        ]

        # Count by event type
        event_types = Counter(e.get("event", "unknown") for e in recent_events)

        # Count by severity
        severities = Counter(e.get("levelname", "INFO") for e in recent_events)

        # Failed authentication attempts
        auth_failures = [
            e
            for e in recent_events
            if e.get("event") in ["auth_failure", "jwt_login_failed"]
        ]

        # Suspicious activities
        suspicious = [
            e for e in recent_events if e.get("event") == "suspicious_request"
        ]

        # Top IPs
        ips = [e.get("ip_address") for e in recent_events if e.get("ip_address")]
        top_ips = Counter(ips).most_common(10)

        # Top users
        users = [e.get("username") for e in recent_events if e.get("username")]
        top_users = Counter(users).most_common(10)

        # Rate limit exceeded
        rate_limited = [
            e for e in recent_events if e.get("event") == "rate_limit_exceeded"
        ]

        # Blocked IPs
        blocked_ips = [e for e in recent_events if e.get("event") == "ip_blocked"]

        return {
            "total_events": len(recent_events),
            "event_types": dict(event_types),
            "severities": dict(severities),
            "auth_failures": len(auth_failures),
            "suspicious_activities": len(suspicious),
            "rate_limited_requests": len(rate_limited),
            "blocked_ips": len(blocked_ips),
            "top_ips": top_ips,
            "top_users": top_users,
            "recent_suspicious": suspicious[-10:] if suspicious else [],
            "recent_auth_failures": auth_failures[-10:] if auth_failures else [],
        }

    def _is_recent(self, timestamp_str, cutoff):
        """Check if timestamp is recent."""
        try:
            # Try various timestamp formats
            from dateutil import parser

            timestamp = parser.parse(timestamp_str)
            return timestamp >= cutoff
        except Exception:
            # If can't parse, include it
            return True

    def _print_analysis(self, analysis):
        """Print analysis in human-readable format."""
        self.stdout.write(f"Total Events: {analysis['total_events']}\n")
        self._print_event_types(analysis["event_types"])
        self._print_severities(analysis["severities"])
        self._print_security_metrics(analysis)
        self._print_top_entities("IP Addresses", analysis["top_ips"])
        self._print_top_entities("Users", analysis["top_users"])
        self._print_recent_events(
            "Suspicious Activities", analysis["recent_suspicious"], formatter=self._format_message_event
        )
        self._print_recent_events(
            "Auth Failures", analysis["recent_auth_failures"], formatter=self._format_auth_failure
        )

    def _print_event_types(self, event_types):
        self.stdout.write(self.style.SUCCESS("\nEvent Types:"))
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"  {event_type}: {count}")

    def _print_severities(self, severities):
        self.stdout.write(self.style.SUCCESS("\nSeverity Levels:"))
        for severity, count in sorted(severities.items()):
            style = self._severity_style(severity)
            self.stdout.write(style(f"  {severity}: {count}"))

    def _print_security_metrics(self, analysis):
        self.stdout.write(self.style.WARNING("\nSecurity Metrics:"))
        metrics = {
            "Failed Authentication Attempts": analysis["auth_failures"],
            "Suspicious Activities": analysis["suspicious_activities"],
            "Rate Limited Requests": analysis["rate_limited_requests"],
            "Blocked IPs": analysis["blocked_ips"],
        }
        for label, value in metrics.items():
            self.stdout.write(f"  {label}: {value}")

    def _print_top_entities(self, label, entries, unit: str = "requests"):
        if not entries:
            return
        self.stdout.write(self.style.SUCCESS(f"\nTop {label}:"))
        for name, count in entries[:5]:
            self.stdout.write(f"  {name}: {count} {unit}")

    def _print_recent_events(self, label, events, formatter):
        if not events:
            return
        self.stdout.write(
            self.style.WARNING(
                f"\nRecent {label} ({len(events)}):"
            )
        )
        for event in events[-5:]:
            self.stdout.write(f"  {formatter(event)}")
        self.stdout.write("\n")

    def _format_message_event(self, event):
        return f"{event.get('asctime', 'N/A')}: {event.get('message', 'N/A')}"

    def _format_auth_failure(self, event):
        timestamp = event.get("asctime", "N/A")
        username = event.get("username", "unknown")
        ip_address = event.get("ip_address", "unknown")
        return f"{timestamp}: {username} from {ip_address}"

    def _severity_style(self, severity):
        if severity == "ERROR":
            return self.style.ERROR
        if severity == "WARNING":
            return self.style.WARNING
        return self.style.SUCCESS
