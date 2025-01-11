class RoleTags:
    TOOL = "tool_prefix"
    USER = "user_prefix"
    ASSISTANT = "ai_prefix"
    SYSTEM = "sys_prefix"
    CONTENT = "content_prefix"


class RoleNames:
    TOOL = "tool"
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "assistant"

    @staticmethod
    def to_tag(role) -> RoleTags:
        if role == RoleNames.ASSISTANT:
            return RoleTags.ASSISTANT
        elif role == RoleNames.USER:
            return RoleTags.USER
        elif role == RoleNames.SYSTEM:
            return RoleTags.SYSTEM

        return RoleTags.TOOL