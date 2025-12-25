from django.shortcuts import redirect

def role_required(roles=[]):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                return redirect('login')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# from django.http import HttpResponseForbidden

# def role_required(allowed_roles):
#     def decorator(view_func):
#         def wrapper(request, *args, **kwargs):
#             if request.user.role not in allowed_roles:
#                 return HttpResponseForbidden("Access Denied")
#             return view_func(request, *args, **kwargs)
#         return wrapper
#     return decorator
