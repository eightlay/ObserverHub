from enum import Enum


class GeneralEvent(Enum):
    # Join
    JOIN = "JOIN"
    JOIN_ACCEPTED = "JOIN_ACCEPTED"
    # Leave
    LEAVE = "LEAVE"
    LEAVE_SUCCESS = "LEAVE_SUCCESS"
    # Error
    ERROR = "ERROR"


class PublisherEvent(Enum):
    # Create topic
    CREATE_TOPICS = "CREATE_TOPICS"
    CREATE_TOPICS_INVALID = "CREATE_TOPICS_INVALID"
    CREATE_TOPICS_SUCCESS = "CREATE_TOPICS_SUCCESS"
    # Delete topic
    DELETE_TOPICS = "DELETE_TOPICS"
    DELETE_TOPICS_INVALID = "DELETE_TOPICS_INVALID"
    DELETE_TOPICS_SUCCESS = "DELETE_TOPICS_SUCCESS"
    # Request topics
    REQUEST_TOPICS = "REQUEST_TOPICS"
    REQUEST_TOPICS_INVALID = "REQUEST_TOPICS_INVALID"
    REQUEST_TOPICS_SUCCESS = "REQUEST_TOPICS_SUCCESS"
    # Publish
    PUBLISH = "PUBLISH"
    PUBLISH_INVALID = "PUBLISH_INVALID"
    PUBLISH_SUCCESS = "PUBLISH_SUCCESS"


class SubscriberEvent(Enum):
    # Subscribe
    SUBSCRIBE = "SUBSCRIBE"
    SUBSCRIBE_INVALID = "SUBSCRIBE_INVALID"
    SUBSCRIBE_SUCCESS = "SUBSCRIBE_SUCCESS"
    # Unsubscribe
    UNSUBSCRIBE = "UNSUBSCRIBE"
    UNSUBSCRIBE_INVALID = "UNSUBSCRIBE_INVALID"
    UNSUBSCRIBE_SUCCESS = "UNSUBSCRIBE_SUCCESS"
    # Update
    UPDATE = "UPDATE"


class Event:
    GENERAL = GeneralEvent
    PUBLISHER = PublisherEvent
    SUBSCRIBER = SubscriberEvent
