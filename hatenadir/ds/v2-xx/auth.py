from twisted.web import resource

# Handle "authentication"
class PyResource(resource.Resource):
        def __init__(self):
                resource.Resource.__init__(self)
        def render(self, request):
                request.setResponseCode(401)
                
                return "what're you looking at?"

