import logging
from typing import Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import mongomock

from app.core.config import settings

logger = logging.getLogger("smartmarks.db")

class Database:
    client: Any = None
    db: Any = None
    is_mock: bool = False

    def connect(self) -> None:
        """Establish connection to MongoDB Atlas or local MongoDB; fallback to mongomock."""
        try:
            # Attempt real MongoDB connection with short server selection timeout
            real_client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500
            )
            # Ping to verify
            real_client.admin.command("ping")
            self.client = real_client
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.is_mock = False
            logger.info("Connected successfully to MongoDB at %s (Database: %s)", settings.MONGODB_URI, settings.MONGODB_DB_NAME)
        except (ConnectionFailure, Exception) as err:
            logger.warning(
                "MongoDB not reachable (%s). Falling back to mongomock for local development/testing.",
                str(err)
            )
            self.client = mongomock.MongoClient()
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.is_mock = True

        self._ensure_indexes()
        self._seed_initial_data_if_empty()

    def _ensure_indexes(self) -> None:
        """Create composite and unique indexes for fast lookups and consistency."""
        try:
            # Exams: unique exam_id
            self.db.exams.create_index([("exam_id", ASCENDING)], unique=True)
            self.db.exams.create_index([("subject_code", ASCENDING), ("exam_type", ASCENDING)])
            
            # Students: unique student_id / roll_number
            self.db.students.create_index([("student_id", ASCENDING)], unique=True)
            self.db.students.create_index([("semester", ASCENDING), ("branch", ASCENDING)])

            # Marks records: unique record_id and unique per student/exam (excluding UNKNOWN pending review)
            self.db.marks_records.create_index([("record_id", ASCENDING)], unique=True)
            self.db.marks_records.create_index(
                [("exam_id", ASCENDING), ("student_id", ASCENDING)],
                unique=True,
                partialFilterExpression={"student_id": {"$ne": "UNKNOWN"}}
            )
            self.db.marks_records.create_index([("status", ASCENDING)])

            # Audit events: sorted by timestamp descending
            self.db.audit_events.create_index([("timestamp", DESCENDING)])
        except Exception as e:
            logger.warning("Index creation notice: %s", str(e))

    def _seed_initial_data_if_empty(self) -> None:
        """Populate initial starter records if collections are empty."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        # Seed students if empty
        if self.db.students.count_documents({}) == 0:
            sample_students = [
                {"student_id": "2023CS0101", "name": "Aarav Sharma", "semester": 3, "branch": "Computer Science", "email": "aarav.sharma@college.edu", "created_at": now},
                {"student_id": "2023CS0102", "name": "Bhavna Patel", "semester": 3, "branch": "Computer Science", "email": "bhavna.patel@college.edu", "created_at": now},
                {"student_id": "2023CS0103", "name": "Chetan Verma", "semester": 3, "branch": "Computer Science", "email": "chetan.verma@college.edu", "created_at": now},
                {"student_id": "2023CS0104", "name": "Divya Nair", "semester": 3, "branch": "Computer Science", "email": "divya.nair@college.edu", "created_at": now},
                {"student_id": "2023CS0105", "name": "Eshan Gupta", "semester": 3, "branch": "Computer Science", "email": "eshan.gupta@college.edu", "created_at": now},
                {"student_id": "2023EC0201", "name": "Farhan Ali", "semester": 5, "branch": "Electronics", "email": "farhan.ali@college.edu", "created_at": now},
                {"student_id": "2023EC0202", "name": "Gauri Deshmukh", "semester": 5, "branch": "Electronics", "email": "gauri.d@college.edu", "created_at": now},
            ]
            self.db.students.insert_many(sample_students)
            logger.info("Seeded %d initial student records.", len(sample_students))

        # Seed initial sample exam if empty
        if self.db.exams.count_documents({}) == 0:
            sample_exam = {
                "exam_id": "EXAM-2026-CS301-MID",
                "title": "Data Structures & Algorithms Mid-Sem",
                "subject_code": "CS301",
                "subject_name": "Data Structures and Algorithms",
                "exam_type": "MID_SEMESTER",
                "semester": 3,
                "academic_year": "2025-2026",
                "exam_date": "2026-11-15",
                "total_marks": 30.0,
                "created_by": "FAC001",
                "questions": [
                    {"question_id": "Q1a", "display_name": "Q1(a)", "max_marks": 5.0, "parent_question": "Q1"},
                    {"question_id": "Q1b", "display_name": "Q1(b)", "max_marks": 5.0, "parent_question": "Q1"},
                    {"question_id": "Q2", "display_name": "Q2", "max_marks": 10.0, "parent_question": None},
                    {"question_id": "Q3", "display_name": "Q3", "max_marks": 10.0, "parent_question": None},
                ],
                "created_at": now,
                "updated_at": now,
            }
            self.db.exams.insert_one(sample_exam)
            
            # Initial audit event
            self.db.audit_events.insert_one({
                "event_type": "EXAM_CREATED",
                "entity_type": "EXAM",
                "entity_id": "EXAM-2026-CS301-MID",
                "description": "Initial examination session CS301 created with 4 questions (30 max marks).",
                "user_id": "FAC001",
                "timestamp": now,
                "metadata": {"exam_type": "MID_SEMESTER", "total_marks": 30.0}
            })
            logger.info("Seeded initial CS301 examination session.")

    def close(self) -> None:
        if self.client:
            self.client.close()


db_instance = Database()

def get_db() -> Any:
    if db_instance.db is None:
        db_instance.connect()
    return db_instance.db

