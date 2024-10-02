from django.test import SimpleTestCase, Client


class ViewTests(SimpleTestCase):
    def test_home_page_response(self):
        client = Client()
        resp = client.get('/')
        self.assertEqual(resp.status_code, 200)

