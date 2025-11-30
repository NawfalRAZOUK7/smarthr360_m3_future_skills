"""
Log Analysis Management Command
Analyzes application logs for errors, performance issues, and patterns.
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    """Analyze application logs."""

    help = "Analyze application logs for errors, performance, and patterns"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--log-file",
            type=str,
            default="logs/application.log",
            help="Log file to analyze (default: logs/application.log)",
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Hours of logs to analyze (default: 24)",
        )
        parser.add_argument(
            "--errors-only",
            action="store_true",
            help="Show only errors",
        )
        parser.add_argument(
            "--performance",
            action="store_true",
            help="Show performance analysis",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output in JSON format",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=10,
            help="Number of top items to show (default: 10)",
        )

    def handle(self, *args, **options):
        """Execute command."""
        log_file = options["log_file"]
        hours = options["hours"]
        errors_only = options["errors_only"]
        show_performance = options["performance"]
        json_output = options["json"]
        top_n = options["top"]

        # Resolve log file path
        if not os.path.isabs(log_file):
            log_file = os.path.join(settings.BASE_DIR, log_file)

        if not os.path.exists(log_file):
            self.stdout.write(self.style.ERROR(f"Log file not found: {log_file}"))
            return

        if not json_output:
            self.stdout.write(self.style.HTTP_INFO("=" * 80))
            self.stdout.write(self.style.HTTP_INFO("Log Analysis"))
            self.stdout.write(self.style.HTTP_INFO("=" * 80))
            self.stdout.write(f"Log file: {log_file}")
            self.stdout.write(f"Time range: Last {hours} hours")
            self.stdout.write("")

        # Parse logs
        logs = self._parse_log_file(log_file, hours)

        if not logs:
            self.stdout.write(
                self.style.WARNING("No logs found in specified time range")
            )
            return

        # Analyze logs
        analysis = self._analyze_logs(logs, errors_only, show_performance, top_n)

        # Output results
        if json_output:
            self.stdout.write(json.dumps(analysis, indent=2, default=str))
        else:
            self._print_analysis(analysis, errors_only, show_performance)

    def _parse_log_file(self, log_file: str, hours: int) -> List[Dict[str, Any]]:
        """Parse log file and filter by time."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        logs = []

        with open(log_file, "r") as f:
            for line in f:
                try:
                    # Try to parse as JSON
                    log_entry = json.loads(line.strip())

                    # Parse timestamp
                    timestamp_str = log_entry.get(
                        "timestamp", log_entry.get("time", "")
                    )
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(
                                timestamp_str.replace("Z", "+00:00")
                            )
                            if timestamp.tzinfo:
                                timestamp = timestamp.replace(tzinfo=None)

                            if timestamp >= cutoff_time:
                                log_entry["_parsed_timestamp"] = timestamp
                                logs.append(log_entry)
                        except ValueError:
                            pass

                except json.JSONDecodeError:
                    # Try to parse as plain text
                    if line.strip():
                        logs.append({"message": line.strip(), "format": "text"})

        return logs

    def _analyze_logs(
        self,
        logs: List[Dict[str, Any]],
        errors_only: bool,
        show_performance: bool,
        top_n: int,
    ) -> Dict[str, Any]:
        """Analyze parsed logs."""
        analysis = {
            "total_logs": len(logs),
            "time_range": {
                "start": min(
                    log.get("_parsed_timestamp", datetime.now()) for log in logs
                ),
                "end": max(
                    log.get("_parsed_timestamp", datetime.now()) for log in logs
                ),
            },
        }

        # Count by level
        level_counts = Counter(log.get("level", "UNKNOWN") for log in logs)
        analysis["by_level"] = dict(level_counts)

        # Error analysis
        errors = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]
        analysis["errors"] = {
            "count": len(errors),
            "by_type": dict(
                Counter(log.get("event", "unknown") for log in errors).most_common(
                    top_n
                )
            ),
            "recent": errors[-top_n:] if errors else [],
        }

        # Performance analysis
        if show_performance:
            performance_logs = [
                log
                for log in logs
                if "duration_seconds" in log or "response_time" in log
            ]

            if performance_logs:
                durations = [
                    log.get("duration_seconds", log.get("response_time", 0))
                    for log in performance_logs
                ]

                analysis["performance"] = {
                    "total_requests": len(performance_logs),
                    "avg_duration": sum(durations) / len(durations) if durations else 0,
                    "min_duration": min(durations) if durations else 0,
                    "max_duration": max(durations) if durations else 0,
                    "slow_requests": [
                        log
                        for log in performance_logs
                        if log.get("duration_seconds", log.get("response_time", 0))
                        > 1.0
                    ][:top_n],
                }

        # Request analysis
        request_logs = [log for log in logs if "path" in log and "method" in log]
        if request_logs:
            endpoints = [
                f"{log.get('method')} {log.get('path')}" for log in request_logs
            ]

            analysis["requests"] = {
                "total": len(request_logs),
                "by_endpoint": dict(Counter(endpoints).most_common(top_n)),
                "by_method": dict(Counter(log.get("method") for log in request_logs)),
                "by_status": dict(
                    Counter(log.get("status_code") for log in request_logs)
                ),
            }

        # User analysis
        user_logs = [log for log in logs if "user_id" in log and log.get("user_id")]
        if user_logs:
            analysis["users"] = {
                "active_users": len(set(log.get("user_id") for log in user_logs)),
                "top_users": dict(
                    Counter(log.get("user_id") for log in user_logs).most_common(top_n)
                ),
            }

        return analysis

    def _print_analysis(
        self, analysis: Dict[str, Any], errors_only: bool, show_performance: bool
    ):
        """Print analysis in human-readable format."""
        if not errors_only:
            # Summary
            self.stdout.write(self.style.HTTP_INFO("Summary:"))
            self.stdout.write(self.style.HTTP_INFO("-" * 80))
            self.stdout.write(f"Total logs: {analysis['total_logs']}")
            self.stdout.write(
                f"Time range: {analysis['time_range']['start']} to {analysis['time_range']['end']}"
            )
            self.stdout.write("")

            # By level
            self.stdout.write(self.style.HTTP_INFO("Log Levels:"))
            self.stdout.write(self.style.HTTP_INFO("-" * 80))
            for level, count in sorted(
                analysis["by_level"].items(), key=lambda x: x[1], reverse=True
            ):
                if level in ["ERROR", "CRITICAL"]:
                    self.stdout.write(self.style.ERROR(f"  {level}: {count}"))
                elif level == "WARNING":
                    self.stdout.write(self.style.WARNING(f"  {level}: {count}"))
                else:
                    self.stdout.write(f"  {level}: {count}")
            self.stdout.write("")

        # Errors
        if analysis["errors"]["count"] > 0:
            self.stdout.write(self.style.HTTP_INFO("Errors:"))
            self.stdout.write(self.style.HTTP_INFO("-" * 80))
            self.stdout.write(
                self.style.ERROR(f"Total errors: {analysis['errors']['count']}")
            )

            if analysis["errors"]["by_type"]:
                self.stdout.write("")
                self.stdout.write("Top error types:")
                for error_type, count in analysis["errors"]["by_type"].items():
                    self.stdout.write(f"  {error_type}: {count}")

            if analysis["errors"]["recent"]:
                self.stdout.write("")
                self.stdout.write("Recent errors:")
                for error in analysis["errors"]["recent"][-5:]:
                    timestamp = error.get("_parsed_timestamp", "unknown")
                    message = error.get("message", error.get("event", "unknown"))
                    self.stdout.write(f"  [{timestamp}] {message}")

            self.stdout.write("")

        # Performance
        if show_performance and "performance" in analysis:
            perf = analysis["performance"]
            self.stdout.write(self.style.HTTP_INFO("Performance:"))
            self.stdout.write(self.style.HTTP_INFO("-" * 80))
            self.stdout.write(f"Total requests: {perf['total_requests']}")
            self.stdout.write(f"Avg duration: {perf['avg_duration']:.3f}s")
            self.stdout.write(f"Min duration: {perf['min_duration']:.3f}s")
            self.stdout.write(f"Max duration: {perf['max_duration']:.3f}s")

            if perf["slow_requests"]:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        f"Slow requests (> 1s): {len(perf['slow_requests'])}"
                    )
                )
                for req in perf["slow_requests"][:5]:
                    duration = req.get("duration_seconds", req.get("response_time", 0))
                    path = req.get("path", "unknown")
                    method = req.get("method", "unknown")
                    self.stdout.write(f"  {method} {path}: {duration:.3f}s")

            self.stdout.write("")

        # Requests
        if not errors_only and "requests" in analysis:
            req = analysis["requests"]
            self.stdout.write(self.style.HTTP_INFO("Requests:"))
            self.stdout.write(self.style.HTTP_INFO("-" * 80))
            self.stdout.write(f"Total requests: {req['total']}")

            if req["by_endpoint"]:
                self.stdout.write("")
                self.stdout.write("Top endpoints:")
                for endpoint, count in list(req["by_endpoint"].items())[:5]:
                    self.stdout.write(f"  {endpoint}: {count}")

            self.stdout.write("")
