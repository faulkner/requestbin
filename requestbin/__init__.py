from cStringIO import StringIO

from flask import Flask
from werkzeug.contrib.fixers import ProxyFix


class WSGIRawBody(object):
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):

        length = environ.get('CONTENT_LENGTH', '0')
        length = 0 if length == '' else int(length)

        body = environ['wsgi.input'].read(length)
        environ['raw'] = body
        environ['wsgi.input'] = StringIO(body)

        # Call the wrapped application
        app_iter = self.application(environ, self._sr_callback(start_response))

        # Return modified response
        return app_iter

    def _sr_callback(self, start_response):
        def callback(status, headers, exc_info=None):

            # Call upstream start_response
            start_response(status, headers, exc_info)
        return callback


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('requestbin.config')
app.config.from_pyfile('application.cfg', silent=True)

app.wsgi_app = WSGIRawBody(ProxyFix(app.wsgi_app))

if app.config.get('BUGSNAG_KEY'):
    import bugsnag
    from bugsnag.flask import handle_exceptions
    bugsnag.configure(
        api_key=app.config['BUGSNAG_KEY'],
        project_root=app.root_path,
        release_stage=app.config.get('REALM'),
        notify_release_stages=["production", "test"],
        use_ssl=True
    )
    handle_exceptions(app)

from filters import *
app.jinja_env.filters['status_class'] = status_class
app.jinja_env.filters['friendly_time'] = friendly_time
app.jinja_env.filters['friendly_size'] = friendly_size
app.jinja_env.filters['to_qs'] = to_qs
app.jinja_env.filters['approximate_time'] = approximate_time
app.jinja_env.filters['exact_time'] = exact_time
app.jinja_env.filters['short_date'] = short_date

app.add_url_rule('/', 'views.home')
app.add_url_rule('/<name>', 'views.bin', methods=['GET', 'POST', 'DELETE', 'PUT', 'OPTIONS', 'HEAD', 'PATCH', 'TRACE'])

app.add_url_rule('/docs/<name>', 'views.docs')
app.add_url_rule('/api/v1/bins', 'api.bins', methods=['POST'])
app.add_url_rule('/api/v1/bins/<name>', 'api.bin', methods=['GET'])
app.add_url_rule('/api/v1/bins/<bin>/requests', 'api.requests', methods=['GET'])
app.add_url_rule('/api/v1/bins/<bin>/requests/<name>', 'api.request', methods=['GET'])

app.add_url_rule('/api/v1/stats', 'api.stats')

# app.add_url_rule('/robots.txt', redirect_to=url_for('static', filename='robots.txt'))

from requestbin import api, views
