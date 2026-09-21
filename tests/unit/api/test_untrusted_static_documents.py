from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.app import SafeStaticFiles

def test_direct_uploaded_html_navigation_is_sandboxed(tmp_path):
    (tmp_path/'source.html').write_text('<script>parent.document.body.innerHTML="bad"</script>')
    (tmp_path/'image.svg').write_text('<svg onload="alert(1)"></svg>')
    app=FastAPI();app.mount('/projects',SafeStaticFiles(directory=tmp_path))
    with TestClient(app) as client:
        for file in ['source.html','image.svg']:
            response=client.get('/projects/'+file)
            assert response.status_code==200
            assert 'sandbox' in response.headers['content-security-policy']
            assert "default-src 'none'" in response.headers['content-security-policy']
            assert response.headers['x-content-type-options']=='nosniff'
            assert response.headers['cache-control']=='no-store'
