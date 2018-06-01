import functools


class TeamcityError(Exception):
    def __init__(self, error_message="", response_code=None,
                 response_body=None):

        Exception.__init__(self, error_message)
        # Http status code
        self.response_code = response_code
        # Full http response
        self.response_body = response_body
        # Parsed error message from teamcity
        self.error_message = error_message

    def __str__(self):
        if self.response_code is not None:
            return "{0}: {1}".format(self.response_code, self.error_message)
        else:
            return "{0}".format(self.error_message)

class TeamcityAuthenticationError(TeamcityError):
    pass


class TeamcityParsingError(TeamcityError):
    pass


class TeamcityConnectionError(TeamcityError):
    pass


class TeamcityOperationError(TeamcityError):
    pass


class TeamcityHttpError(TeamcityError):
    pass


class TeamcityListError(TeamcityOperationError):
    pass


class TeamcityGetError(TeamcityOperationError):
    pass


class TeamcityCreateError(TeamcityOperationError):
    pass


class TeamcityUpdateError(TeamcityOperationError):
    pass


class TeamcityDeleteError(TeamcityOperationError):
    pass


class TeamcitySetError(TeamcityOperationError):
    pass


class TeamcityProtectError(TeamcityOperationError):
    pass


class TeamcityTransferProjectError(TeamcityOperationError):
    pass


class TeamcityProjectDeployKeyError(TeamcityOperationError):
    pass


class TeamcityCancelError(TeamcityOperationError):
    pass


class TeamcityPipelineCancelError(TeamcityCancelError):
    pass


class TeamcityRetryError(TeamcityOperationError):
    pass


class TeamcityBuildCancelError(TeamcityCancelError):
    pass


class TeamcityBuildRetryError(TeamcityRetryError):
    pass


class TeamcityBuildPlayError(TeamcityRetryError):
    pass


class TeamcityBuildEraseError(TeamcityRetryError):
    pass


class TeamcityJobCancelError(TeamcityCancelError):
    pass


class TeamcityJobRetryError(TeamcityRetryError):
    pass


class TeamcityJobPlayError(TeamcityRetryError):
    pass


class TeamcityJobEraseError(TeamcityRetryError):
    pass


class TeamcityPipelineRetryError(TeamcityRetryError):
    pass


class TeamcityBlockError(TeamcityOperationError):
    pass


class TeamcityUnblockError(TeamcityOperationError):
    pass


class TeamcitySubscribeError(TeamcityOperationError):
    pass


class TeamcityUnsubscribeError(TeamcityOperationError):
    pass


class TeamcityMRForbiddenError(TeamcityOperationError):
    pass


class TeamcityMRClosedError(TeamcityOperationError):
    pass


class TeamcityMROnBuildSuccessError(TeamcityOperationError):
    pass


class TeamcityTodoError(TeamcityOperationError):
    pass


class TeamcityTimeTrackingError(TeamcityOperationError):
    pass


class TeamcityUploadError(TeamcityOperationError):
    pass


class TeamcityAttachFileError(TeamcityOperationError):
    pass


class TeamcityCherryPickError(TeamcityOperationError):
    pass


class TeamcityHousekeepingError(TeamcityOperationError):
    pass


class TeamcityOwnershipError(TeamcityOperationError):
    pass

def on_http_error(error):
    """Manage TeamcityHttpError exceptions.

    This decorator function can be used to catch TeamcityHttpError exceptions
    raise specialized exceptions instead.

    Args:
        error(Exception): The exception type to raise -- must inherit from
            TeamcityError
    """
    def wrap(f):
        @functools.wraps(f)
        def wrapped_f(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except TeamcityHttpError as e:
                raise error(e.error_message, e.response_code, e.response_body)
        return wrapped_f
    return wrap
