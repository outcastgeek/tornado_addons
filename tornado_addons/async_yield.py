from types import GeneratorType
import tornado.web

class WrappedCall(object):
    def __init__(self, func, *a, **ka):
        self.func = func
        self.a = a
        self.ka = ka
        self.yielding = None

    def _yield_continue(self, response=None):
        try: self.yielding.send(response)
        except StopIteration: pass

    def yield_cb(self, *args, **ka):
        """
        A generic callback for yielded async calls that just captures all args
        and kwargs then continues execution.

        Notes about retval
        ------------------
        If a single value is returned into the callback, that value is returned
        as the value of a yield expression.

        i.e.: x = yield http.fetch(uri, self.mycb)

        The response from the fetch will be returned to x.

        If more than one value is returned, but no kwargs, the retval is the
        args tuple.  If there are kwargs but no args, then retval is kwargs.
        If there are both args and kwargs, retval = (args, kwargs).  If none,
        retval is None.

        It's a little gross but works for a large majority of the cases.
        """
        if args and ka:
            self._yield_continue((args, ka))
        elif ka and not args:
            self._yield_continue(ka)
        elif args and not ka:
            if len(args) == 1:
                # flatten it
                self._yield_continue(args[0])
            else:
                self._yield_continue(args)
        else:
            self._yield_continue()

    def __enter__(self):
        # munge this instance's yield_cb to map to THIS instance of a context
        obj = self.a[0]
        self.old_yield_cb = obj.yield_cb
        obj.yield_cb = self.yield_cb
        print "enter", self.func
        self.yielding = self.func(*self.a, **self.ka)
        return self.yielding

    def __exit__(self, exc_type, exc_value, traceback):
        obj = self.a[0]
        print "exit", obj, self.func
        # obj.yield_cb = self.old_yield_cb


def async_yield(f):
    def yielding_(*a, **ka):
        with WrappedCall(f, *a, **ka) as f_:
            if type(f_) is not GeneratorType:
                print "F_ not a generator", f_
                return f_

            print "F_ gen", f_
            try: 
                f_.next() # kickstart it
                print "f_ went", f_
            except StopIteration:
                print "STOP ITER", f_
                pass

    return yielding_


class AsyncYieldMixin(tornado.web.RequestHandler):

    yield_cb = lambda *a, **ka: None

    def prepare(self):
        self._yield_callbacks = {}
        super(AsyncYieldMixin, self).prepare()

    def add_func_callback(self, _id, cb):
        self._yield_callbacks[_id] = cb
        print "adding", _id, cb

    def rm_func_callback(self, _id):
        del self._yield_callbacks[_id]


