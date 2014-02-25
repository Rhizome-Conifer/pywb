import webtest
from pywb.pywb_init import pywb_config
from pywb.wbapp import create_wb_app
from pywb.cdx.cdxobject import CDXObject

class TestWb:
    TEST_CONFIG = 'test_config.yaml'

    def setup(self):
        #self.app = pywb.wbapp.create_wb_app(pywb.pywb_init.pywb_config())
        self.app = create_wb_app(pywb_config(self.TEST_CONFIG))
        self.testapp = webtest.TestApp(self.app)

    def _assert_basic_html(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/html'
        assert resp.content_length > 0

    def _assert_basic_text(self, resp):
        assert resp.status_int == 200
        assert resp.content_type == 'text/plain'
        assert resp.content_length > 0

    def test_home(self):
        resp = self.testapp.get('/')
        self._assert_basic_html(resp)
        assert '/pywb' in resp.body

    def test_pywb_root(self):
        resp = self.testapp.get('/pywb/')
        self._assert_basic_html(resp)
        assert 'Search' in resp.body

    def test_calendar_query(self):
        resp = self.testapp.get('/pywb/*/iana.org')
        self._assert_basic_html(resp)
        # 3 Captures + header
        assert len(resp.html.find_all('tr')) == 4

    def test_calendar_query_filtered(self):
        # unfiltered collection
        resp = self.testapp.get('/pywb/*/http://www.iana.org/_css/2013.1/screen.css')
        self._assert_basic_html(resp)
        # 17 Captures + header
        assert len(resp.html.find_all('tr')) == 18

        # filtered collection
        resp = self.testapp.get('/pywb-filt/*/http://www.iana.org/_css/2013.1/screen.css')
        self._assert_basic_html(resp)
        # 1 Capture (filtered) + header
        assert len(resp.html.find_all('tr')) == 2

    def test_calendar_query_fuzzy_match(self):
        # fuzzy match removing _= according to standard rules.yaml
        resp = self.testapp.get('/pywb/*/http://www.iana.org/_css/2013.1/screen.css?_=3141592653')
        self._assert_basic_html(resp)
        # 17 Captures + header
        assert len(resp.html.find_all('tr')) == 18

    def test_cdx_query(self):
        resp = self.testapp.get('/pywb/cdx_/*/http://www.iana.org/')
        self._assert_basic_text(resp)

        assert '20140127171238 http://www.iana.org/ warc/revisit - OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB' in resp
        # check for 3 cdx lines (strip final newline)
        actual_len = len(str(resp.body).rstrip().split('\n'))
        assert actual_len == 3, actual_len


    def test_replay_1(self):
        resp = self.testapp.get('/pywb/20140127171238/http://www.iana.org/')
        self._assert_basic_html(resp)

        assert 'Mon, Jan 27 2014 17:12:38' in resp.body
        assert 'wb.js' in resp.body
        assert '/pywb/20140127171238/http://www.iana.org/time-zones' in resp.body

    def test_replay_content_length_1(self):
        # test larger file, rewritten file (svg!)
        resp = self.testapp.get('/pywb/20140126200654/http://www.iana.org/_img/2013.1/rir-map.svg')
        assert resp.headers['Content-Length'] == str(len(resp.body))


    def test_redirect_1(self):
        resp = self.testapp.get('/pywb/20140127171237/http://www.iana.org/')
        assert resp.status_int == 302

        assert resp.headers['Location'].endswith('/pywb/20140127171238/http://iana.org')


    def test_redirect_replay_2(self):
        resp = self.testapp.get('/pywb/http://example.com/')
        assert resp.status_int == 302

        assert resp.headers['Location'].endswith('/20140127171251/http://example.com')
        resp = resp.follow()

        #check resp
        self._assert_basic_html(resp)
        assert 'Mon, Jan 27 2014 17:12:51' in resp.body
        assert '/pywb/20140127171251/http://www.iana.org/domains/example' in resp.body

    def test_redirect_relative_3(self):
        # first two requests should result in same redirect
        target = 'http://localhost:8080/pywb/2014/http://iana.org/_css/2013.1/screen.css'

        # without timestamp
        resp = self.testapp.get('/_css/2013.1/screen.css', headers = [('Referer', 'http://localhost:8080/pywb/2014/http://iana.org/')])
        assert resp.status_int == 302
        assert resp.headers['Location'] == target, resp.headers['Location']

        # with timestamp
        resp = self.testapp.get('/2014/_css/2013.1/screen.css', headers = [('Referer', 'http://localhost:8080/pywb/2014/http://iana.org/')])
        assert resp.status_int == 302
        assert resp.headers['Location'] == target, resp.headers['Location']


        resp = resp.follow()
        assert resp.status_int == 302
        assert resp.headers['Location'].endswith('/pywb/20140127171239/http://www.iana.org/_css/2013.1/screen.css')

        resp = resp.follow()
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'


    def test_referrer_self_redirect(self):
        uri = '/pywb/20140127171239/http://www.iana.org/_css/2013.1/screen.css'
        host = 'somehost:8082'
        referrer = 'http://' + host + uri

        # capture is normally a 200
        resp = self.testapp.get(uri)
        assert resp.status_int == 200

        # redirect causes skip of this capture, redirect to next
        resp = self.testapp.get(uri, headers = [('Referer', referrer), ('Host', host)], status = 302)
        assert resp.status_int == 302


    def test_excluded_content(self):
        resp = self.testapp.get('/pywb/http://www.iana.org/_img/bookmark_icon.ico', status = 403)
        assert resp.status_int == 403
        assert 'Excluded' in resp.body


    def test_static_content(self):
        resp = self.testapp.get('/static/test/route/wb.css')
        assert resp.status_int == 200
        assert resp.content_type == 'text/css'
        assert resp.content_length > 0


    # 'Simulating' proxy by settings REQUEST_URI explicitly to http:// url and no SCRIPT_NAME
    # would be nice to be able to test proxy more
    def test_proxy_replay(self):
        resp = self.testapp.get('/x-ignore-this-x', extra_environ = dict(REQUEST_URI = 'http://www.iana.org/domains/idn-tables', SCRIPT_NAME = ''))
        self._assert_basic_html(resp)

        assert 'Sun, Jan 26 2014 20:11:27' in resp.body
        assert 'wb.js' in resp.body

    def test_proxy_pac(self):
        resp = self.testapp.get('/proxy.pac', extra_environ = dict(SERVER_NAME='pywb-proxy', SERVER_PORT='8080'))
        assert resp.content_type == 'application/x-ns-proxy-autoconfig'
        assert '"PROXY pywb-proxy:8080"' in resp.body
        assert '"localhost"' in resp.body

    def test_cdx_server_filters(self):
        resp = self.testapp.get('/pywb-cdx?url=http://www.iana.org/_css/2013.1/screen.css&filter=mimetype:warc/revisit&filter=filename:dupes.warc.gz')
        self._assert_basic_text(resp)
        actual_len = len(resp.body.rstrip().split('\n'))
        assert actual_len == 1, actual_len

    def test_cdx_server_advanced(self):
        # combine collapsing, reversing and revisit resolving
        resp = self.testapp.get('/pywb-cdx?url=http://www.iana.org/_css/2013.1/print.css&collapseTime=11&resolveRevisits=true&reverse=true')

        # convert back to CDXObject
        cdxs = map(CDXObject, resp.body.rstrip().split('\n'))
        assert len(cdxs) == 3, len(cdxs)

        # verify timestamps
        timestamps = map(lambda cdx: cdx['timestamp'], cdxs)
        assert timestamps == ['20140127171239', '20140126201054', '20140126200625']

        # verify orig filenames (2 revisits, one non)
        origfilenames = map(lambda cdx: cdx['orig.filename'], cdxs)
        assert origfilenames == ['iana.warc.gz', 'iana.warc.gz', '-']


    def test_error(self):
        resp = self.testapp.get('/pywb/?abc', status = 400)
        assert resp.status_int == 400
        assert 'Invalid Url: http://?abc' in resp.body

#=================================================================
# Reporter callback for replay view
class PrintReporter:
    def __call__(self, wbrequest, cdx, response):
        print wbrequest
        print cdx
        pass

#=================================================================
class TestExclusionPerms:
    """
    Sample Perm Checker which allows all
    """
    def allow_url_lookup(self, urlkey, url):
        """
        Return true/false if url or urlkey (canonicalized url)
        should be allowed
        """
        print urlkey
        if urlkey == 'org,iana)/_img/bookmark_icon.ico':
            return False

        return True

    def allow_capture(self, cdx):
        """
        Return true/false is specified capture (cdx) should be
        allowed
        """
        return True

    def filter_fields(self, cdx):
        """
        Filter out any forbidden cdx fields from cdx dictionary
        """
        return cdx


