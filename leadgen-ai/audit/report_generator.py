"""
Audit Report Generator.
Produces clean, professional audit reports from stored audit data.
Supports terminal display (CLI) and HTML export (for clients).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from database.connection import Database
from database.models import Audit, Lead
from config.settings import Config

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / 'data' / 'reports'


class AuditReportGenerator:
    """Generates audit reports from database records."""

    def __init__(self):
        Database.initialize()

    # ─── Terminal Report (CLI) ──────────────────────────────

    def print_report(self, lead_id: int) -> bool:
        """Print a full audit report to the terminal."""
        session = Database.get_session()

        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error(f"Lead #{lead_id} not found")
            session.close()
            return False

        audit = (
            session.query(Audit)
            .filter(Audit.lead_id == lead_id)
            .order_by(Audit.audit_timestamp.desc())
            .first()
        )
        if not audit:
            logger.error(f"No audit data for lead #{lead_id} ({lead.business_name})")
            session.close()
            return False

        raw = audit.raw_data or {}
        issues = audit.major_issues or []
        cwv = raw.get('core_web_vitals', {})

        w = 60  # report width

        print()
        print('═' * w)
        print(f'  WEBSITE AUDIT REPORT')
        print(f'  {lead.business_name}')
        print('═' * w)
        print(f'  URL:       {lead.website_url}')
        print(f'  Industry:  {lead.industry or "—"}')
        print(f'  Location:  {lead.location or "—"}')
        print(f'  Audited:   {audit.audit_timestamp.strftime("%B %d, %Y at %I:%M %p") if audit.audit_timestamp else "—"}')
        print(f'  Status:    {audit.audit_status.upper()}')
        print('─' * w)

        # ── Scores ──
        print(f'\n SCORES')
        print(f'  {"─" * 40}')
        self._print_score_bar('Performance', audit.performance_score, w)
        self._print_score_bar('SEO', audit.seo_score, w)
        self._print_score_bar('Accessibility', audit.accessibility_score, w)
        bp = raw.get('best_practices_score')
        if bp is not None:
            self._print_score_bar('Best Practices', bp, w)
        print(f'  Mobile Friendly:  {"✅ Yes" if audit.mobile_friendly else "❌ No"}')

        # ── Core Web Vitals ──
        if cwv:
            print(f'\n CORE WEB VITALS')
            print(f'  {"─" * 40}')
            for key in ['lcp', 'fcp', 'inp', 'cls', 'tbt', 'speed_index']:
                metric = cwv.get(key)
                if metric:
                    label = metric.get('label', key.upper())
                    value = metric.get('value', '—')
                    score = metric.get('score')
                    grade = self._grade(score) if score is not None else '—'
                    print(f'  {label:<30} {value:<12} {grade}')

        # ── Technical Details ──
        print(f'\n TECHNICAL DETAILS')
        print(f'  {"─" * 40}')
        checks = [
            ('SSL/HTTPS', raw.get('ssl_valid'), raw.get('has_ssl')),
            ('Page Title', raw.get('has_title'), None),
            ('Meta Description', raw.get('has_meta_description'), None),
            ('Viewport (Mobile)', raw.get('has_viewport'), None),
            ('Open Graph Tags', raw.get('has_og_tags'), None),
            ('Favicon', raw.get('has_favicon'), None),
        ]
        for label, primary, fallback in checks:
            val = primary if primary is not None else fallback
            if val is True:
                print(f'  {label:<30} ✅ Present')
            elif val is False:
                print(f'  {label:<30} ❌ Missing')
            else:
                print(f'  {label:<30} ⚠️  Unknown')

        title = raw.get('title', '')
        if title:
            print(f'  Page Title:  "{title}"')

        h1 = raw.get('h1_count', 0)
        if h1 == 0:
            print(f'  H1 Headings: ❌ None found')
        elif h1 == 1:
            print(f'  H1 Headings: ✅ 1 (correct)')
        else:
            print(f'  H1 Headings: ⚠️  {h1} found (should be 1)')

        load_ms = raw.get('load_time_ms')
        if load_ms:
            load_s = load_ms / 1000
            grade = '✅' if load_s < 3 else '⚠️' if load_s < 5 else '❌'
            print(f'  Load Time:   {grade} {load_s:.1f}s')

        # ── Issues Found ──
        if issues:
            critical = [i for i in issues if i.get('severity') == 'critical']
            warnings = [i for i in issues if i.get('severity') != 'critical']

            print(f'\n ISSUES FOUND ({len(issues)} total)')
            print(f'  {"─" * 40}')

            if critical:
                print(f'\n  Critical ({len(critical)}):')
                for i, issue in enumerate(critical, 1):
                    print(f'    {i}. {issue["issue"]}')
                    if issue.get('details'):
                        print(f'       → {issue["details"]}')

            if warnings:
                print(f'\n  Warnings ({len(warnings)}):')
                for i, issue in enumerate(warnings, 1):
                    print(f'    {i}. {issue["issue"]}')
                    if issue.get('details'):
                        print(f'       → {issue["details"]}')

        print()
        print('═' * w)
        print(f'  Report by {Config.BUSINESS_NAME}')
        print(f'  {Config.BUSINESS_EMAIL}')
        print('═' * w)
        print()

        session.close()
        return True

    def print_all_reports(self):
        """Print summary table of all audited leads."""
        session = Database.get_session()
        results = (
            session.query(Audit, Lead)
            .join(Lead)
            .order_by(Audit.audit_timestamp.desc())
            .all()
        )

        if not results:
            print("No audits found.")
            session.close()
            return

        print()
        print(f'{"ID":<4} {"Business":<30} {"Perf":>5} {"SEO":>5} {"Acc":>5} {"Mobile":>8} {"Issues":>7} {"Status":<10}')
        print('─' * 80)
        for audit, lead in results:
            issues_count = len(audit.major_issues) if audit.major_issues else 0
            mobile = '✅' if audit.mobile_friendly else '❌'
            print(
                f'{lead.id:<4} '
                f'{lead.business_name[:28]:<30} '
                f'{audit.performance_score or 0:>5} '
                f'{audit.seo_score or 0:>5} '
                f'{audit.accessibility_score or 0:>5} '
                f'{mobile:>8} '
                f'{issues_count:>7} '
                f'{audit.audit_status:<10}'
            )
        print()
        session.close()

    # ─── HTML Export ────────────────────────────────────────

    def export_html(self, lead_id: int) -> Optional[str]:
        """Export a single audit report as a professional HTML file."""
        session = Database.get_session()

        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error(f"Lead #{lead_id} not found")
            session.close()
            return None

        audit = (
            session.query(Audit)
            .filter(Audit.lead_id == lead_id)
            .order_by(Audit.audit_timestamp.desc())
            .first()
        )
        if not audit:
            logger.error(f"No audit data for lead #{lead_id}")
            session.close()
            return None

        raw = audit.raw_data or {}
        issues = audit.major_issues or []
        cwv = raw.get('core_web_vitals', {})

        # Build HTML
        html = self._build_html(lead, audit, raw, issues, cwv)

        # Save
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = lead.business_name.replace(' ', '_').replace(',', '').replace("'", '')
        filename = f'audit_{safe_name}_{lead.id}.html'
        filepath = REPORTS_DIR / filename

        filepath.write_text(html, encoding='utf-8')
        logger.info(f"✓ Audit report saved: {filepath}")

        session.close()
        return str(filepath)

    def export_all_html(self) -> List[str]:
        """Export all audit reports as individual HTML files."""
        session = Database.get_session()
        leads_with_audits = (
            session.query(Lead)
            .join(Audit)
            .distinct()
            .all()
        )
        session.close()

        paths = []
        for lead in leads_with_audits:
            path = self.export_html(lead.id)
            if path:
                paths.append(path)

        return paths

    # ─── Helpers ────────────────────────────────────────────

    @staticmethod
    def _grade(score) -> str:
        if score is None:
            return '—'
        if score >= 90:
            return '🟢 Good'
        if score >= 50:
            return '🟡 Needs Work'
        return '🔴 Poor'

    @staticmethod
    def _grade_class(score) -> str:
        if score is None:
            return 'unknown'
        if score >= 90:
            return 'good'
        if score >= 50:
            return 'average'
        return 'poor'

    @staticmethod
    def _print_score_bar(label: str, score, width: int):
        if score is None:
            print(f'  {label:<20} — (no data)')
            return
        filled = int(score / 5)  # 20 chars max
        bar = '█' * filled + '░' * (20 - filled)
        grade = '🟢' if score >= 90 else '🟡' if score >= 50 else '🔴'
        print(f'  {label:<20} {bar} {score}/100  {grade}')

    def _build_html(self, lead, audit, raw, issues, cwv) -> str:
        """Build a clean, professional HTML report."""
        audit_date = audit.audit_timestamp.strftime('%B %d, %Y') if audit.audit_timestamp else '—'

        # Score cards
        scores = [
            ('Performance', audit.performance_score),
            ('SEO', audit.seo_score),
            ('Accessibility', audit.accessibility_score),
            ('Best Practices', raw.get('best_practices_score')),
        ]
        score_cards = ''
        for label, score in scores:
            val = score if score is not None else 0
            cls = self._grade_class(score)
            score_cards += f'''
            <div class="score-card {cls}">
                <div class="score-value">{val}</div>
                <div class="score-label">{label}</div>
            </div>'''

        # Core Web Vitals rows
        cwv_rows = ''
        if cwv:
            for key in ['lcp', 'fcp', 'inp', 'cls', 'tbt', 'speed_index']:
                metric = cwv.get(key)
                if metric:
                    cls = self._grade_class(metric.get('score'))
                    cwv_rows += f'''
                    <tr>
                        <td>{metric.get("label", key.upper())}</td>
                        <td>{metric.get("value", "—")}</td>
                        <td class="{cls}">{metric.get("score", "—")}/100</td>
                    </tr>'''

        # Technical checks
        check_rows = ''
        checks = [
            ('SSL / HTTPS', raw.get('ssl_valid', raw.get('has_ssl'))),
            ('Page Title', raw.get('has_title')),
            ('Meta Description', raw.get('has_meta_description')),
            ('Mobile Viewport', raw.get('has_viewport')),
            ('Open Graph Tags', raw.get('has_og_tags')),
            ('Favicon', raw.get('has_favicon')),
            ('Mobile Friendly', audit.mobile_friendly),
        ]
        for label, val in checks:
            if val is True:
                status = '<span class="pass">✅ Pass</span>'
            elif val is False:
                status = '<span class="fail">❌ Fail</span>'
            else:
                status = '<span class="warn">⚠️ Unknown</span>'
            check_rows += f'<tr><td>{label}</td><td>{status}</td></tr>'

        # Issues
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        warning_issues = [i for i in issues if i.get('severity') != 'critical']

        issues_html = ''
        if critical_issues:
            issues_html += '<h3>🚨 Critical Issues</h3><ul class="issues critical">'
            for issue in critical_issues:
                detail = f' — <em>{issue["details"]}</em>' if issue.get('details') else ''
                issues_html += f'<li>{issue["issue"]}{detail}</li>'
            issues_html += '</ul>'

        if warning_issues:
            issues_html += '<h3>⚠️ Warnings</h3><ul class="issues warnings">'
            for issue in warning_issues:
                detail = f' — <em>{issue["details"]}</em>' if issue.get('details') else ''
                issues_html += f'<li>{issue["issue"]}{detail}</li>'
            issues_html += '</ul>'

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Audit — {lead.business_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a2e;
            background: #f8f9fa;
            padding: 2rem;
        }}
        .report {{
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            padding: 2.5rem;
        }}
        .header h1 {{ font-size: 1.5rem; font-weight: 600; margin-bottom: 0.3rem; }}
        .header .subtitle {{ opacity: 0.8; font-size: 0.95rem; }}
        .header .meta {{ margin-top: 1rem; font-size: 0.85rem; opacity: 0.7; }}
        .header .meta span {{ margin-right: 1.5rem; }}

        .content {{ padding: 2rem 2.5rem; }}
        h2 {{
            font-size: 1.15rem;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e8e8e8;
            color: #1a1a2e;
        }}
        h2:first-child {{ margin-top: 0; }}

        .scores {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin: 1rem 0;
        }}
        .score-card {{
            text-align: center;
            padding: 1.2rem 0.5rem;
            border-radius: 10px;
            border: 2px solid #e8e8e8;
        }}
        .score-card.good {{ border-color: #27ae60; background: #f0faf4; }}
        .score-card.average {{ border-color: #f39c12; background: #fef9f0; }}
        .score-card.poor {{ border-color: #e74c3c; background: #fdf0ef; }}
        .score-value {{ font-size: 2rem; font-weight: 700; }}
        .good .score-value {{ color: #27ae60; }}
        .average .score-value {{ color: #f39c12; }}
        .poor .score-value {{ color: #e74c3c; }}
        .score-label {{ font-size: 0.8rem; color: #666; margin-top: 0.3rem; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0.5rem 0;
        }}
        th, td {{
            padding: 0.6rem 0.8rem;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{ font-weight: 600; color: #555; font-size: 0.85rem; }}
        td {{ font-size: 0.9rem; }}
        td.good {{ color: #27ae60; font-weight: 600; }}
        td.average {{ color: #f39c12; font-weight: 600; }}
        td.poor {{ color: #e74c3c; font-weight: 600; }}

        .pass {{ color: #27ae60; }}
        .fail {{ color: #e74c3c; }}
        .warn {{ color: #f39c12; }}

        h3 {{ font-size: 1rem; margin: 1.5rem 0 0.5rem; color: #333; }}
        ul.issues {{ list-style: none; padding: 0; }}
        ul.issues li {{
            padding: 0.6rem 0.8rem;
            margin: 0.3rem 0;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        ul.critical li {{ background: #fdf0ef; border-left: 3px solid #e74c3c; }}
        ul.warnings li {{ background: #fef9f0; border-left: 3px solid #f39c12; }}
        ul.issues li em {{ color: #666; font-size: 0.85rem; }}

        .footer {{
            margin-top: 2rem;
            padding: 1.5rem 2.5rem;
            background: #f8f9fa;
            border-top: 1px solid #eee;
            font-size: 0.85rem;
            color: #888;
        }}
        .footer strong {{ color: #1a1a2e; }}

        @media (max-width: 600px) {{
            .scores {{ grid-template-columns: repeat(2, 1fr); }}
            body {{ padding: 0.5rem; }}
            .content {{ padding: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="report">
        <div class="header">
            <h1>Website Audit Report</h1>
            <div class="subtitle">{lead.business_name}</div>
            <div class="meta">
                <span>🌐 {lead.website_url}</span>
                <span>📅 {audit_date}</span>
            </div>
        </div>

        <div class="content">
            <h2>Performance Scores</h2>
            <div class="scores">
                {score_cards}
            </div>

            {"<h2>Core Web Vitals</h2>" if cwv_rows else ""}
            {"<table><tr><th>Metric</th><th>Value</th><th>Score</th></tr>" + cwv_rows + "</table>" if cwv_rows else ""}

            <h2>Technical Checks</h2>
            <table>
                <tr><th>Check</th><th>Status</th></tr>
                {check_rows}
            </table>

            <h2>Issues Found ({len(issues)})</h2>
            {issues_html if issues_html else "<p>No significant issues detected.</p>"}
        </div>

        <div class="footer">
            Report generated by <strong>{Config.BUSINESS_NAME}</strong><br>
            {Config.BUSINESS_EMAIL}
        </div>
    </div>
</body>
</html>'''
