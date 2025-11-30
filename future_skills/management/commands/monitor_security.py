"""
Security Event Monitor
======================

Django management command to monitor and analyze security events.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
import json
import re
from collections import Counter, defaultdict


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
        except:
            # If can't parse, include it
            return True

    def _print_analysis(self, analysis):
        """Print analysis in human-readable format."""
        self.stdout.write(f"Total Events: {analysis['total_events']}\n")

        # Event types
        self.stdout.write(self.style.SUCCESS("\nEvent Types:"))
        for event_type, count in sorted(
            analysis["event_types"].items(), key=lambda x: x[1], reverse=True
        ):
            self.stdout.write(f"  {event_type}: {count}")

        # Severities
        self.stdout.write(self.style.SUCCESS("\nSeverity Levels:"))
        for severity, count in sorted(analysis["severities"].items()):
            style = (
                self.style.ERROR
                if severity == "ERROR"
                else self.style.WARNING if severity == "WARNING" else self.style.SUCCESS
            )
            self.stdout.write(style(f"  {severity}: {count}"))

        # Security metrics
        self.stdout.write(self.style.WARNING("\nSecurity Metrics:"))
        self.stdout.write(
            f"  Failed Authentication Attempts: {analysis['auth_failures']}"
        )
        self.stdout.write(
            f"  Suspicious Activities: {analysis['suspicious_activities']}"
        )
        self.stdout.write(
            f"  Rate Limited Requests: {analysis['rate_limited_requests']}"
        )
        self.stdout.write(f"  Blocked IPs: {analysis['blocked_ips']}")

        # Top IPs
        if analysis["top_ips"]:
            self.stdout.write(self.style.SUCCESS("\nTop IP Addresses:"))
            for ip, count in analysis["top_ips"][:5]:
                self.stdout.write(f"  {ip}: {count} requests")

        # Top users
        if analysis["top_users"]:
            self.stdout.write(self.style.SUCCESS("\nTop Users:"))
            for user, count in analysis["top_users"][:5]:
                self.stdout.write(f"  {user}: {count} requests")

        # Recent suspicious activities
        if analysis["recent_suspicious"]:
            self.stdout.write(
                self.style.WARNING(
                    f'\nRecent Suspicious Activities ({len(analysis["recent_suspicious"])}):'
                )
            )
            for event in analysis["recent_suspicious"][-5:]:
                self.stdout.write(
                    f"  {event.get('asctime', 'N/A')}: {event.get('message', 'N/A')}"
                )

        # Recent auth failures
        if analysis["recent_auth_failures"]:
            self.stdout.write(
                self.style.WARNING(
                    f'\nRecent Auth Failures ({len(analysis["recent_auth_failures"])}):'
                )
            )
            for event in analysis["recent_auth_failures"][-5:]:
                self.stdout.write(
                    f"  {event.get('asctime', 'N/A')}: {event.get('username', 'unknown')} from {event.get('ip_address', 'unknown')}"
                )

        self.stdout.write("\n")
