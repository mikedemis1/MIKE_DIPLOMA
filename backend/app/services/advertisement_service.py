# backend/app/services/advertisement_service.py
from typing import List, Optional
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
        ΠΡΙΝ: φιλτράραμε ανά zone_id (WHERE zone = %s).

        ΤΩΡΑ: για τις ανάγκες του GEO-ADS UI,
        θέλουμε ΟΛΕΣ οι διαφημίσεις να είναι διαθέσιμες
        σε ΟΛΕΣ τις ζώνες (GlassFloor, Surrounding, Megatron).

        Άρα αγνοούμε το zone_id και επιστρέφουμε όλες τις εγγραφές.
        Κρατάμε όμως την παράμετρο για συμβατότητα με το API.
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
    def get_by_id(ad_id: int) -> Optional[Advertisement]:
        """
        Επιστρέφει μία διαφήμιση με βάση το id.
        Αν δεν βρεθεί, γυρνάει None.
        """
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, name, image_url, zone
            FROM advertisements
            WHERE id = %s;
            """,
            (ad_id,),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if row is None:
            return None

        return Advertisement(
            id=row[0],
            name=row[1],
            image_url=row[2],
            zone=row[3],
        )
