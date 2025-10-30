"""
Report generation utilities
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from jinja2 import Template


class Reporter:
    """Generate investigation reports"""

    def __init__(self):
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)

    def generate_report(self, data: Dict[str, Any], output_path: str, format: str = 'both'):
        """Generate report in specified format(s)"""
        output_path = Path(output_path)

        if format in ['json', 'both']:
            self._generate_json(data, f"{output_path}.json")

        if format in ['html', 'both']:
            self._generate_html(data, f"{output_path}.html")

    def _generate_json(self, data: Dict[str, Any], filepath: str):
        """Generate JSON report"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _generate_html(self, data: Dict[str, Any], filepath: str):
        """Generate HTML report"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        template = Template(self._get_html_template())
        html = template.render(
            data=data,
            generated_at=datetime.utcnow().isoformat(),
            target=data.get('target', 'Unknown'),
            inv_type=data.get('type', 'unknown').upper()
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

    def _get_html_template(self) -> str:
        """HTML template for reports"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSINT Investigation Report - {{ target }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .summary {
            padding: 30px 40px;
            background: #f8f9fa;
            border-bottom: 3px solid #667eea;
        }
        .summary h2 {
            color: #667eea;
            margin-bottom: 20px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .summary-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary-item .label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        .summary-item .value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        .results {
            padding: 40px;
        }
        .results h2 {
            color: #667eea;
            margin-bottom: 30px;
        }
        .result-card {
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .result-card h3 {
            color: #333;
            margin-bottom: 15px;
        }
        .result-card .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.partial { background: #fff3cd; color: #856404; }
        .status.skipped { background: #e2e3e5; color: #383d41; }
        .result-data {
            background: white;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
        }
        .accounts-list {
            list-style: none;
        }
        .accounts-list li {
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #667eea;
        }
        .accounts-list a {
            color: #667eea;
            text-decoration: none;
            word-break: break-all;
        }
        .accounts-list a:hover {
            text-decoration: underline;
        }
        .footer {
            background: #333;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .warning strong {
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 OSINT Investigation Report</h1>
            <div class="subtitle">{{ inv_type }} Investigation</div>
        </div>

        <div class="summary">
            <h2>📊 Investigation Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Target</div>
                    <div class="value">{{ target }}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Type</div>
                    <div class="value">{{ inv_type }}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Modules Run</div>
                    <div class="value">{{ data.modules_run }}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Successful Checks</div>
                    <div class="value">{{ data.successful_checks }}</div>
                </div>
            </div>
        </div>

        <div class="results">
            <h2>🔎 Detailed Results</h2>

            {% if data.type == 'username' and data.accounts %}
            <div class="warning">
                <strong>⚠️ Found {{ data.accounts|length }} accounts</strong>
            </div>
            <ul class="accounts-list">
                {% for account in data.accounts %}
                <li>
                    <strong>{{ account.site or account.platform }}:</strong>
                    <a href="{{ account.url }}" target="_blank">{{ account.url }}</a>
                </li>
                {% endfor %}
            </ul>
            {% endif %}

            {% for result in data.results %}
            <div class="result-card">
                <h3>{{ result.module }} - {{ result.source }}</h3>
                <span class="status {{ result.status }}">{{ result.status|upper }}</span>
                <div class="result-data">
                    <pre>{{ result.data|tojson(indent=2) }}</pre>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="footer">
            <p>Generated: {{ generated_at }}</p>
            <p>OSINT Investigator v1.0.0</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                ⚠️ This report is for authorized security research and investigations only.
            </p>
        </div>
    </div>
</body>
</html>
        """
