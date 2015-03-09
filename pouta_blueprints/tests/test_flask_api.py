import unittest
import base64
import json

from pouta_blueprints.tests.base import db, BaseTestCase
from pouta_blueprints.models import User, Blueprint, Plugin, ActivationToken, Instance


class FlaskApiTestCase(BaseTestCase):
    def setUp(self):
        db.create_all()
        u1 = User("admin@example.org", "admin", is_admin=True)
        u2 = User("user@example.org", "user", is_admin=False)

        db.session.add(u1)
        db.session.add(u2)
        p1 = Plugin()
        p1.name = "TestPlugin"
        self.known_plugin_id = p1.visual_id
        db.session.add(p1)

        r1 = Blueprint()
        r1.name = "TestBlueprint"
        r1.plugin = p1.visual_id
        r2 = Blueprint()
        r2.name = "EnabledTestBlueprint"
        r2.plugin = p1.visual_id
        r2.is_enabled = True
        db.session.add(r1)
        db.session.add(r2)
        self.known_blueprint_id = r2.visual_id

        db.session.commit()

        i1 = Instance(
            Blueprint.query.filter_by(visual_id=r2.visual_id).first().id,
            User.query.filter_by(email="user@example.org").first().id)
        db.session.add(i1)
        self.known_instance_id = i1.visual_id

        db.session.commit()

    def make_request(self, method='GET', path='/', headers={}, data=None):
        methods = {
            'GET': self.client.get,
            'POST': self.client.post
        }

        assert method in methods

        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        headers = [(x, y) for x, y in headers.items()]
        return methods[method](path, headers=headers, data=data, content_type='application/json')

    def make_authenticated_request(self, method='GET', path='/', headers={}, data=None, creds=None):
        assert creds is not None

        methods = {
            'GET': self.client.get,
            'POST': self.client.post
        }

        assert method in methods

        response = self.make_request('POST', '/api/v1/sessions',
                                     headers=headers,
                                     data=json.dumps(creds))
        token = '%s:' % response.json['token']
        token_b64 = base64.b64encode(bytes(token.encode('ascii'))).decode('utf-8')

        headers = {
            'Accept': 'application/json',
            'Authorization': 'Basic %s' % token_b64,
            'token': token_b64
        }
        return methods[method](path, headers=headers, data=data, content_type='application/json')

    def make_authenticated_admin_request(self, method='GET', path='/', headers={}, data=None):
        return self.make_authenticated_request(method, path, headers, data, creds={'email': 'admin@example.org', 'password': 'admin'})

    def make_authenticated_user_request(self, method='GET', path='/', headers={}, data=None):
        return self.make_authenticated_request(method, path, headers, data, creds={'email': 'user@example.org', 'password': 'user'})

    def test_first_user(self):
        db.drop_all()
        db.create_all()
        response = self.make_request('POST',
                                     '/api/v1/initialize',
                                     data=json.dumps({'email': 'admin@example.org',
                                                      'password': 'admin'}))
        self.assert_200(response)

    def test_anonymous_get_users(self):
        response = self.make_request(path='/api/v1/users')
        self.assert_401(response)

    def test_user_get_users(self):
        response = self.make_authenticated_user_request(path='/api/v1/users')
        self.assertEqual(len(response.json), 1)
        self.assert_200(response)

    def test_admin_get_users(self):
        response = self.make_authenticated_admin_request(path='/api/v1/users')
        self.assert_200(response)

    def test_anonymous_get_plugins(self):
        response = self.make_request(path='/api/v1/plugins')
        self.assert_401(response)

    def test_user_get_plugins(self):
        response = self.make_authenticated_user_request(path='/api/v1/plugins')
        self.assert_403(response)

    def test_admin_get_plugins(self):
        response = self.make_authenticated_admin_request(path='/api/v1/plugins')
        self.assert_200(response)

    def test_anonymous_get_single_plugin(self):
        response = self.make_request(path='/api/v1/plugins/%s' % self.known_plugin_id)
        self.assert_401(response)

    def test_authenticated_user_get_single_plugin(self):
        response = self.make_authenticated_user_request(path='/api/v1/plugins/%s' % self.known_plugin_id)
        self.assert_403(response)

    def test_authenticated_admin_get_single_plugin(self):
        response = self.make_authenticated_admin_request(path='/api/v1/plugins/%s' % self.known_plugin_id)
        self.assert_200(response)

    def test_anonymous_get_blueprints(self):
        response = self.make_request(path='/api/v1/blueprints')
        self.assert_401(response)

    def test_user_get_blueprints(self):
        response = self.make_authenticated_user_request(path='/api/v1/blueprints')
        self.assert_200(response)
        self.assertEqual(len(response.json), 1)

    def test_admin_get_blueprints(self):
        response = self.make_authenticated_admin_request(path='/api/v1/blueprints')
        self.assert_200(response)
        self.assertEqual(len(response.json), 2)

    def test_anonymous_invite_user(self):
        data = {'email': 'test@example.org', 'password': 'test', 'is_admin': True}
        response = self.make_request(
            method='POST',
            path='/api/v1/users',
            data=json.dumps(data))
        self.assert_401(response)

    def test_user_invite_user(self):
        data = {'email': 'test@example.org', 'password': 'test', 'is_admin': True}
        response = self.make_authenticated_user_request(
            method='POST',
            path='/api/v1/users',
            data=json.dumps(data))
        self.assert_403(response)

    def test_admin_invite_user(self):
        data = {'email': 'test@example.org', 'password': 'test', 'is_admin': True}
        response = self.make_authenticated_admin_request(
            method='POST',
            path='/api/v1/users',
            data=json.dumps(data))
        self.assert_200(response)
        user = User.query.filter_by(email='test@example.org').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_admin)

    def test_accept_invite(self):
        user = User.query.filter_by(email='test@example.org').first()
        self.assertIsNone(user)
        data = {'email': 'test@example.org', 'password': None, 'is_admin': True}
        response = self.make_authenticated_admin_request(
            method='POST',
            path='/api/v1/users',
            data=json.dumps(data))
        self.assert_200(response)
        user = User.query.filter_by(email='test@example.org').first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active)
        token = ActivationToken.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(token)
        data = {'password': 'testtest'}
        response = self.make_request(
            method='POST',
            path='/api/v1/activations/%s' % token.token,
            data=json.dumps(data))
        self.assert_200(response)
        user = User.query.filter_by(email='test@example.org').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)

    def test_anonymous_create_instance(self):
        data = {'blueprint_id': self.known_blueprint_id}
        response = self.make_request(
            method='POST',
            path='/api/v1/instances',
            data=json.dumps(data))
        self.assert_401(response)

    def test_user_create_instance(self):
        data = {'blueprint': self.known_blueprint_id}
        response = self.make_authenticated_user_request(
            method='POST',
            path='/api/v1/instances',
            data=json.dumps(data))
        self.assert_200(response)

    def test_anonymous_get_instances(self):
        response = self.make_request(path='/api/v1/instances')
        self.assert_401(response)

    def test_user_get_instances(self):
        response = self.make_authenticated_user_request(path='/api/v1/instances')
        self.assert_200(response)
        self.assertEqual(len(response.json), 1)

    def test_admin_get_instances(self):
        response = self.make_authenticated_admin_request(path='/api/v1/instances')
        self.assert_200(response)
        self.assertEqual(len(response.json), 1)

    def test_anonymous_get_instance(self):
        response = self.make_request(path='/api/v1/instances/%s' % self.known_instance_id)
        self.assert_401(response)

    def test_user_get_instance(self):
        response = self.make_authenticated_user_request(path='/api/v1/instances/%s' % self.known_instance_id)
        self.assert_200(response)

    def test_admin_get_instance(self):
        response = self.make_authenticated_admin_request(path='/api/v1/instances/%s' % self.known_instance_id)
        self.assert_200(response)


if __name__ == '__main__':
    unittest.main()
