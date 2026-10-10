"""Browser regression checks; Netlify ingestion must be tested after deployment."""
import functools
import os
from pathlib import Path
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit, unquote

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class WebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
            headless=True, args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context(reduced_motion='reduce')
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def visit(self, name):
        response = self.page.goto(f'{self.base}/{name}')
        self.assertEqual(response.status, 200)

    def test_pages_links_assets_and_responsive_layouts(self):
        screenshots = Path('/tmp/harazi-screenshots')
        screenshots.mkdir(exist_ok=True)
        for width in (375, 768, 900, 1024, 1440):
            self.page.set_viewport_size({'width': width, 'height': 900})
            for file in sorted(ROOT.glob('*.html')):
                with self.subTest(width=width, page=file.name):
                    self.visit(file.name)
                    self.assertEqual(self.page.locator('h1').count(), 1)
                    self.assertTrue(self.page.title())
                    self.assertTrue(self.page.locator('html').get_attribute('lang'))
                    self.assertTrue(self.page.evaluate(
                        'document.documentElement.scrollWidth <= innerWidth'))
                    self.assertTrue(self.page.locator('img').evaluate_all(
                        'images => images.every(i => i.complete && i.naturalWidth > 0 && i.alt)'))
                    links = self.page.locator('[href], [src]').evaluate_all(
                        'nodes => nodes.map(n => n.getAttribute("href") || n.getAttribute("src"))')
                    for link in links:
                        parsed = urlsplit(link)
                        if parsed.scheme or parsed.netloc or not parsed.path:
                            continue
                        target = unquote(parsed.path).lstrip('/')
                        self.assertTrue((ROOT / target).is_file(), target)
                        self.assertEqual(self.context.request.get(f'{self.base}/{target}').status, 200)
                    if file.name == 'index.html' and width in (375, 1440):
                        self.page.screenshot(path=str(screenshots / f'home-{width}.png'), full_page=True)

    def test_mobile_keyboard_navigation(self):
        self.page.set_viewport_size({'width': 375, 'height': 812})
        self.visit('index.html')
        self.page.keyboard.press('Tab')
        self.assertEqual(self.page.locator(':focus').inner_text(), 'Skip to content')
        self.page.keyboard.press('Enter')
        self.assertTrue(self.page.url.endswith('#main-content'))
        toggle = self.page.locator('.menu-toggle')
        toggle.click()
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'true')
        self.assertTrue(self.page.get_by_role('navigation', name='Main navigation').is_visible())
        self.page.keyboard.press('Escape')
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'false')
        self.assertTrue(toggle.evaluate('el => el === document.activeElement'))
        toggle.click()
        self.page.mouse.click(10, 650)
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'false')
        toggle.click()
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.assertTrue(self.page.get_by_role('navigation', name='Main navigation').is_visible())
        self.page.set_viewport_size({'width': 375, 'height': 812})
        expect(self.page.get_by_role('navigation', name='Main navigation')).to_be_hidden()

    def test_navigation_without_javascript(self):
        context = self.browser.new_context(java_script_enabled=False, viewport={'width': 375, 'height': 812})
        try:
            page = context.new_page()
            page.goto(f'{self.base}/index.html')
            nav = page.get_by_role('navigation', name='Main navigation')
            self.assertTrue(nav.is_visible())
            nav.get_by_role('link', name='Products', exact=True).click()
            self.assertTrue(page.url.endswith('/products.html'))
        finally:
            context.close()

    def test_inquiry_validation_preselection_and_native_post(self):
        self.visit('inquiry.html?category=Dairy')
        self.assertEqual(self.page.locator('#product').input_value(), 'Dairy')
        self.assertFalse(self.page.locator('form').evaluate('f => f.checkValidity()'))
        form = self.page.locator('form')
        self.assertEqual(form.get_attribute('data-netlify'), 'true')
        self.assertEqual(form.get_attribute('netlify-honeypot'), 'bot-field')
        self.assertEqual(self.page.locator('[name="form-name"]').input_value(), 'wholesale-inquiry')
        for field, value in {'company': 'Test Buyer', 'name': 'Test Contact', 'email': 'buyer@example.com',
                             'country': 'Malaysia', 'qty': '1 container', 'port': 'Port Klang',
                             'notes': 'Test submission only'}.items():
            self.page.locator('#' + field).fill(value)
        self.assertFalse(form.evaluate('f => f.checkValidity()'))
        self.page.locator('#ack').check()
        self.assertTrue(form.evaluate('f => f.checkValidity()'))
        submissions = []

        def receive(route):
            if route.request.method == 'POST':
                submissions.append(parse_qs(route.request.post_data, keep_blank_values=True))
                route.fulfill(status=303, headers={'Location': '/thank-you.html'}, body='')
            else:
                route.continue_()

        self.page.route('**/thank-you.html', receive)
        self.page.get_by_role('button', name='Send Wholesale Inquiry').click()
        self.page.wait_for_url('**/thank-you.html')
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0], {
            'form-name': ['wholesale-inquiry'], 'bot-field': [''], 'company': ['Test Buyer'],
            'contact_person': ['Test Contact'], 'email': ['buyer@example.com'],
            'destination_country': ['Malaysia'], 'category': ['Dairy'], 'quantity': ['1 container'],
            'destination_port': ['Port Klang'], 'notes': ['Test submission only'],
            'privacy_acknowledgment': ['accepted']})
        self.assertTrue(self.page.get_by_role('heading', name='Thank you for your inquiry.').is_visible())
        self.visit('inquiry.html?category=%3Cscript%3Ealert(1)%3C/script%3E')
        self.assertEqual(self.page.locator('#product').input_value(), '')

    def test_corporate_details_and_catalog_qualifications(self):
        self.visit('about.html')
        content = self.page.locator('main').inner_text()
        for detail in ['Harazi General Trading Sdn. Bhd.', '202201006110', 'B2-2-3, Publika',
                       'AL HARAZI & CO FOR INVESTMENT LLC', '1340473', '506, Al Mawalih South',
                       'Al Harazi Group Co., Ltd.', '0605568002147', '18/574 The Base Garden Rama 9']:
            self.assertIn(detail, content)
        self.visit('products.html')
        disclaimer = self.page.locator('.disclaimer').inner_text()
        for qualification in ['stock availability', 'brand authorization', 'regulatory licensing']:
            self.assertIn(qualification, disclaimer)


if __name__ == '__main__':
    unittest.main(verbosity=2)
