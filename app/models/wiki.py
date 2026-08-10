"""Wiki category, page and view data-access methods
(moved verbatim from database.py)."""


class WikiMixin:
       # ---------- Wiki Category CRUD ----------
    def add_wiki_category(self, category, img_filename):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO TblWikiCategory (Category, CatImg) VALUES (%s, %s)',
                    (category, img_filename)
                )

    def get_wiki_categories(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT CategoryId, Category, CatImg FROM TblWikiCategory ORDER BY inserted_date DESC'
        )
        cats = cursor.fetchall()
        conn.close()
        return cats

    def update_wiki_category(self, cat_id, category, img_filename=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if img_filename:
            cursor.execute(
                'UPDATE TblWikiCategory SET Category=%s, CatImg=%s WHERE CategoryId=%s',
                (category, img_filename, cat_id)
            )
        else:
            cursor.execute(
                'UPDATE TblWikiCategory SET Category=%s WHERE CategoryId=%s',
                (category, cat_id)
            )
        conn.commit()
        conn.close()

    def delete_wiki_category(self, cat_id):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM TblWikiCategory WHERE CategoryId=%s', (cat_id,))


    # ---------- Wiki Page CRUD ----------
    def add_wiki_page(self, category_id, title, descr):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO TblWikiPage (CategoryId, Title, Descri) VALUES (%s, %s, %s)',
                    (category_id, title, descr)
                )

    def get_wiki_pages(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wp.WikiId, wp.Title, wp.Descri, wp.InsertedDate, wc.Category, wc.CatImg
            FROM TblWikiPage wp
            JOIN TblWikiCategory wc ON wp.CategoryId = wc.CategoryId
            WHERE wp.RowStatus = 0
            ORDER BY wp.InsertedDate DESC
        ''')
        pages = cursor.fetchall()
        conn.close()
        return pages

    def get_wiki_page(self, wiki_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
            wp.WikiId,
            wp.CategoryId,
            wp.Title,
            wp.Descri,
            wc.CatImg
            FROM TblWikiPage wp
            JOIN TblWikiCategory wc ON wp.CategoryId = wc.CategoryId
            WHERE wp.WikiId = %s
        ''', (wiki_id,))
        page = cursor.fetchone()
        conn.close()
        return page

    def update_wiki_page(self, wiki_id, category_id, title, descr):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'UPDATE TblWikiPage SET CategoryId=%s, Title=%s, Descri=%s WHERE WikiId=%s',
                    (category_id, title, descr, wiki_id)
                )

    def soft_delete_wiki_page(self, wiki_id):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'UPDATE TblWikiPage SET RowStatus=1 WHERE WikiId=%s',
                    (wiki_id,)
                )
        # ---------- Wiki Views CRUD ----------
    def add_wiki_view(self, wiki_id, emp_id):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO TblWikiViews (WikiId, EmployeeId) VALUES (%s, %s)',
                    (wiki_id, emp_id)
                )

    def get_wiki_views(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wv.WikiViewId,
                   wp.Title,
                   e.first_name || ' ' || e.last_name AS employee_name,
                   wv.ViewDateTime
            FROM TblWikiViews wv
            JOIN TblWikiPage  wp ON wv.WikiId     = wp.WikiId
            JOIN tbl_employee e  ON wv.EmployeeId = e.emp_id
            ORDER BY wv.ViewDateTime DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return rows
    def get_wiki_views_filtered(self, start_date=None, end_date=None, wiki_id=None):
        """
        Fetch individual view records, optionally filtering by date range and/or wiki page.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT wv.WikiViewId,
                   wp.Title,
                   e.first_name || ' ' || e.last_name AS employee_name,
                   wv.ViewDateTime
            FROM TblWikiViews wv
            JOIN TblWikiPage wp ON wv.WikiId = wp.WikiId
            JOIN tbl_employee e ON wv.EmployeeId = e.emp_id
        '''
        conditions = []
        params = []
        if start_date:
            conditions.append("wv.ViewDateTime::date >= %s::date")
            params.append(start_date)
        if end_date:
            conditions.append("wv.ViewDateTime::date <= %s::date")
            params.append(end_date)
        if wiki_id:
            conditions.append("wv.WikiId = %s")
            params.append(wiki_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY wv.ViewDateTime DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows


    def get_wiki_view_counts(self, start_date=None, end_date=None):
        """
        Return total view count per wiki page, optionally within a date range.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT wp.WikiId,
                   wp.Title,
                   COUNT(*) AS view_count
            FROM TblWikiViews wv
            JOIN TblWikiPage wp ON wv.WikiId = wp.WikiId
        '''
        conditions = []
        params = []
        if start_date:
            conditions.append("wv.ViewDateTime::date >= %s::date")
            params.append(start_date)
        if end_date:
            conditions.append("wv.ViewDateTime::date <= %s::date")
            params.append(end_date)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " GROUP BY wp.WikiId, wp.Title ORDER BY view_count DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows
