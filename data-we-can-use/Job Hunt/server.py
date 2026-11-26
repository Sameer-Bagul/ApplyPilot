import http.server
import socketserver
import json
import urllib.parse
import os
import mimetypes
from pathlib import Path
from engine.db import get_connection
from engine.pitch_generator import generate_pitch, TEMPLATES, get_contact_search_urls
from engine.live_ingest import run_live_ingestion

PORT = 8080
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"

class CRMRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/stats":
            conn = get_connection()
            c = conn.cursor()

            c.execute("SELECT COUNT(*) FROM companies")
            total_companies = c.fetchone()[0]

            c.execute("SELECT fit_tier, COUNT(*) FROM companies GROUP BY fit_tier")
            companies_by_tier = {r[0]: r[1] for r in c.fetchall()}

            c.execute("SELECT COUNT(*) FROM jobs")
            total_jobs = c.fetchone()[0]

            c.execute("SELECT fit_tier, COUNT(*) FROM jobs GROUP BY fit_tier")
            jobs_by_tier = {r[0]: r[1] for r in c.fetchall()}

            c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
            jobs_by_status = {r[0]: r[1] for r in c.fetchall()}

            c.execute("SELECT COUNT(*) FROM contacts")
            total_contacts = c.fetchone()[0]

            conn.close()

            # Calculate daily goal stats
            applied_today = jobs_by_status.get("Applied Directly", 0) + jobs_by_status.get("Followed Up", 0) + jobs_by_status.get("Screening / OA", 0)
            referrals_today = jobs_by_status.get("Referral Sourced", 0)

            self.send_json({
                "status": "success",
                "stats": {
                    "total_companies": total_companies,
                    "companies_by_tier": companies_by_tier,
                    "total_jobs": total_jobs,
                    "jobs_by_tier": jobs_by_tier,
                    "jobs_by_status": jobs_by_status,
                    "total_contacts": total_contacts,
                    "daily_target": 10,
                    "daily_progress": {
                        "applied": applied_today,
                        "referrals": referrals_today,
                        "total_active_pipeline": total_jobs - jobs_by_status.get("Archived", 0)
                    }
                }
            })
            return

        elif path == "/api/companies":
            conn = get_connection()
            c = conn.cursor()

            search = query.get("search", [""])[0].strip()
            tier = query.get("tier", [""])[0].strip()
            cluster = query.get("cluster", [""])[0].strip()
            limit = int(query.get("limit", [100])[0])
            offset = int(query.get("offset", [0])[0])

            sql = "SELECT * FROM companies WHERE 1=1"
            params = []

            if search:
                sql += " AND (company_name LIKE ? OR category LIKE ? OR pune_cluster LIKE ?)"
                wild = f"%{search}%"
                params.extend([wild, wild, wild])

            if tier:
                sql += " AND fit_tier = ?"
                params.append(tier)

            if cluster:
                sql += " AND pune_cluster LIKE ?"
                params.append(f"%{cluster}%")

            # Count total matching
            count_sql = "SELECT COUNT(*) FROM (" + sql + ")"
            c.execute(count_sql, params)
            total_matches = c.fetchone()[0]

            sql += " ORDER BY CASE fit_tier WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, company_name ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            c.execute(sql, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()

            # omit huge raw_metadata for listing speed
            for r in rows:
                if "raw_metadata" in r:
                    del r["raw_metadata"]

            self.send_json({
                "status": "success",
                "total": total_matches,
                "limit": limit,
                "offset": offset,
                "companies": rows
            })
            return

        elif path == "/api/jobs":
            conn = get_connection()
            c = conn.cursor()

            search = query.get("search", [""])[0].strip()
            tier = query.get("tier", [""])[0].strip()
            status_filter = query.get("status", [""])[0].strip()

            sql = "SELECT * FROM jobs WHERE 1=1"
            params = []

            if search:
                sql += " AND (company_name LIKE ? OR job_title LIKE ? OR required_skills LIKE ?)"
                wild = f"%{search}%"
                params.extend([wild, wild, wild])

            if tier:
                sql += " AND fit_tier = ?"
                params.append(tier)

            if status_filter:
                sql += " AND status = ?"
                params.append(status_filter)

            sql += " ORDER BY fit_score DESC, created_at DESC"
            c.execute(sql, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()

            for r in rows:
                if r.get("fit_breakdown"):
                    try:
                        r["fit_breakdown"] = json.loads(r["fit_breakdown"])
                    except:
                        pass
                if "raw_metadata" in r:
                    del r["raw_metadata"]

            self.send_json({
                "status": "success",
                "count": len(rows),
                "jobs": rows
            })
            return

        elif path == "/api/contacts":
            conn = get_connection()
            c = conn.cursor()
            search = query.get("search", [""])[0].strip()
            sql = "SELECT * FROM contacts WHERE 1=1"
            params = []
            if search:
                sql += " AND (company_name LIKE ? OR person_name LIKE ? OR role LIKE ?)"
                wild = f"%{search}%"
                params.extend([wild, wild, wild])
            sql += " ORDER BY CASE verification_status WHEN 'Verified Public' THEN 1 ELSE 2 END, company_name ASC"
            c.execute(sql, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()

            self.send_json({
                "status": "success",
                "count": len(rows),
                "contacts": rows
            })
            return

        elif path == "/api/templates":
            self.send_json({
                "status": "success",
                "templates": TEMPLATES
            })
            return

        # Fallback to standard static files
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        if path == "/api/jobs/status":
            job_id = payload.get("job_id")
            new_status = payload.get("status")

            if not job_id or not new_status:
                self.send_json({"status": "error", "message": "job_id and status are required"}, 400)
                return

            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", (new_status, job_id))
            conn.commit()
            conn.close()

            self.send_json({"status": "success", "job_id": job_id, "new_status": new_status})
            return

        elif path == "/api/pitch":
            angle = payload.get("angle", "agentic_rag")
            context = payload.get("context", {})
            pitch = generate_pitch(angle, context)
            self.send_json({"status": "success", "pitch": pitch})
            return

        elif path == "/api/ingest":
            try:
                added, total = run_live_ingestion()
                self.send_json({"status": "success", "added": added, "total": total})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, 500)
            return

        self.send_json({"status": "error", "message": "Endpoint not found"}, 404)

def run_server(port=PORT):
    # Enable address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), CRMRequestHandler) as httpd:
        print(f"================================================================")
        print(f"🚀 Job Hunt Engine CRM Dashboard running at: http://localhost:{port}")
        print(f"================================================================")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
