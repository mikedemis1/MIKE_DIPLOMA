# backend/app/services/advertisement_service.py

from typing import List
from app.config import get_db_connection
from app.models.advertisement import Advertisement


class AdvertisementService:
    @staticmethod
    def get_all() -> List[Advertisement]:
        """
        Επιστρέφει ΟΛΕΣ τις διαφημίσεις από τον πίνακα advertisements.
        """
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, name, image_url, zone
            FROM advertisements
            ORDER BY id;
            """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        ads: List[Advertisement] = []
        for row in rows:
            ads.append(
                Advertisement(
                    id=row[0],
                    name=row[1],
                    image_url=row[2],
                    zone=row[3],
                )
            )
        return ads

    @staticmethod
    def get_by_zone(zone_id: str) -> List[Advertisement]:
        """
        Επιστρέφει όλες τις διαφημίσεις για μια συγκεκριμένη ζώνη.
        π.χ. zone_id = 'glassfloor', 'megatron', 'surrounding' κλπ.
        """
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, name, image_url, zone
            FROM advertisements
            WHERE zone = %s
            ORDER BY id;
            """,
            (zone_id,),
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        ads: List[Advertisement] = []
        for row in rows:
            ads.append(
                Advertisement(
                    id=row[0],
                    name=row[1],
                    image_url=row[2],
                    zone=row[3],
                )
            )
        return ads
