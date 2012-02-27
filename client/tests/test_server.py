class TestServer(object):
    def test_server_communication(self, server):
        response = server.get("/")
        assert response.status_code == 200