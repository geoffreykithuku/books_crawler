import asyncio
from datetime import datetime, timedelta, timezone
from db.client import db
from typing import List, Dict, Any
import csv
import io

async def generate_daily_change_report(format: str = "json") -> str:
    today = datetime.now(timezone.utc).date()
    start_of_day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end_of_day = start_of_day + timedelta(days=1)

    changes_cursor = db.changes.find({
        "changed_at": {
            "$gte": start_of_day,
            "$lt": end_of_day
        }
    }).sort("changed_at", -1)

    changes = await changes_cursor.to_list(length=None)

    if format == "json":
        # Convert ObjectId to string for JSON serialization
        for change in changes:
            if "_id" in change:
                change["_id"] = str(change["_id"])
            if "old" in change and "_id" in change["old"]:
                change["old"]["_id"] = str(change["old"]["_id"])
            if "new" in change and "_id" in change["new"]:
                change["new"]["_id"] = str(change["new"]["_id"])
        return changes
    elif format == "csv":
        if not changes:
            return ""

        # Determine all possible keys from all change documents
        all_keys = set()
        for change in changes:
            all_keys.update(change.keys())
            if "old" in change:
                all_keys.update(f"old.{k}" for k in change["old"].keys())
            if "new" in change:
                all_keys.update(f"new.{k}" for k in change["new"].keys())
        # Exclude raw_html_snapshot and parent nested dict keys (old/new) and _id from CSV
        all_keys = [k for k in all_keys if "raw_html_snapshot" not in k and k not in ("_id", "old", "new")]
        all_keys.sort() # Sort keys for consistent column order

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_keys)
        writer.writeheader()

        for change in changes:
            row = {}
            for key in all_keys:
                if "." in key:
                    parent_key, child_key = key.split(".")
                    if parent_key in change and child_key in change[parent_key]:
                        row[key] = change[parent_key][child_key]
                else:
                    row[key] = change.get(key)
            writer.writerow(row)
        return output.getvalue()
    else:
        raise ValueError("Unsupported format. Choose 'json' or 'csv'.")

if __name__ == "__main__":
    async def test_report():
        # This is a placeholder for testing.
        # In a real scenario, you'd populate your 'changes' collection with test data.
        print("Generating JSON report...")
        json_report = await generate_daily_change_report(format="json")
        print(json_report)
        print("\nGenerating CSV report...")
        csv_report = await generate_daily_change_report(format="csv")
        print(csv_report)

    asyncio.run(test_report())
