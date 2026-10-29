from mangum import Mangum

from admin_web.app import app

handler = Mangum(app, lifespan="off")
