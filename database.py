import sqlite3
from datetime import date
from typing import List, Tuple

from aqt.utils import showInfo

from .logger import log_error, log_info


class LuteDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def build_sql_query(
        self,
        parents_only=False,
        empty_translation=False,
        include_WKI=False,
        cutoff_date=date.today(),
    ):
        """Define SQL query for loading terms which should be passed to Anki"""
        # SELECT query to load information from lute.db (not all fields are used)
        if parents_only:
            base_query = """
                SELECT
                    w.WoText,
                    w.WoTranslation,
                    w.WoLgID,
                    w.WoCreated,
                    t.TgText,
                    w.WoStatusChanged,
                    w.WoTextLC,
                    w.WoID,
                    w.WoStatus,
                    w.WoRomanization,
                    w.WoTokenCount,
                    wi.WiSource,
                    t.TgComment
                FROM
                    words AS w
                LEFT JOIN
                    wordimages AS wi ON w.WoID = wi.WiWoID
                LEFT JOIN
                    wordtags AS wt ON wi.WiWoID = wt.WtWoID
                LEFT JOIN
                    tags AS t ON wt.WtTgID = t.TgID
                LEFT JOIN
                    wordparents AS wp_child ON w.WoID = wp_child.WpWoID
                LEFT JOIN
                    wordparents AS wp_parent ON w.WoID = wp_parent.WpParentWoID
            """
        else:
            base_query = """
                SELECT WoText, WoTranslation, WoLgID, WoCreated, TgText,
                    WoStatusChanged, WoTextLC, WoID, WoStatus, WoRomanization,
                    WiSource, TgComment
                FROM words AS w
                LEFT JOIN wordimages AS wi ON w.WoID = wi.WiWoID
                LEFT JOIN wordtags AS wt ON wi.WiWoID = wt.WtWoID
                LEFT JOIN tags AS t ON wt.WtTgID = t.TgID
            """
        # Put together list of conditions to use as filter
        where_conditions = [
            "WoTranslation IS NOT NULL",
            "(wp_child.WpParentWoID IS NULL OR wp_parent.WpParentWoID IS NOT NULL)",
            f'WoCreated >= "{cutoff_date.isoformat()}"',
        ]

        if not empty_translation:
            where_conditions.append("WoTranslation <> ''")

        if not include_WKI:
            where_conditions.append("WoStatus <= 5")

        include_unknown = False  # TODO: add in options
        if not include_unknown:
            where_conditions.append("1 <= WoStatus")

        # Join all conditions with 'AND'
        where_clause = "WHERE " + " AND ".join(where_conditions)
        log_info("[database] Executing SQL query to fetch terms.")

        return f"{base_query}\n{where_clause};"

    def connect(
        self, parents_only, empty_translation, include_WKI, cutoff_date
    ) -> Tuple[List, List]:
        """Connect to LUTE database and retrieve terms and languages"""
        if not self.db_path.endswith("lute.db"):
            # Checks if file other than lute.db has been selected
            showInfo("Please select a lute.db file")
            log_error(f"[database] Invalid database file selected: {self.db_path}")
            return [], []

        try:
            # Connecting to lute.db
            conn = sqlite3.connect(self.db_path)
            log_info(f"[database] Successfully connected to database: {self.db_path}")
            cursor = conn.cursor()

            # Get terms (dynamic query based on filters)
            cursor.execute(
                self.build_sql_query(
                    parents_only, empty_translation, include_WKI, cutoff_date
                )
            )
            terms = cursor.fetchall()

            # Get languages (pair used language IDs with language names)
            used_lg_ids = list(set(term[2] for term in terms))
            cursor.execute("SELECT * FROM languages")
            all_languages = cursor.fetchall()
            languages = [
                [lang[0], lang[1]] for lang in all_languages if lang[0] in used_lg_ids
            ]

            conn.close()
            log_info(
                f"[database] Retrieved {len(terms)} terms and {len(languages)} languages."
            )
            return terms, languages

        except Exception as e:
            log_error(f"[database] Database connection error: {str(e)}")
            showInfo(f"Database connection error: {str(e)}")
            return [], []
