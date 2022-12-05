# Copyright 2022 Lawrence Livermore National Security, LLC and other
# HPCIC DevTools Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (MIT)


import json


class CloudProvider:
    """
    A base class for a cloud provider
    """

    name = "cloud"

    def __init__(self):

        # If we weren't created with settings, add empty
        if not hasattr(self, "settings"):
            from cloud_select.main.settings import Settings

            self.settings = Settings()

    def __str__(self):
        return str(self.__class__.__name__)

    def load_instances(self, data):
        """
        Load instance data from json.
        """
        raise NotImplementedError

    def instances(self):
        """
        Retrieve all instances for a cloud.
        """
        raise NotImplementedError


class CloudDataEncoder(json.JSONEncoder):
    """
    Make our group and instance classes json serializable.

    Always return the data!
    """

    def default(self, o):
        return o.data


class CloudData:
    """
    An "abstract" class that stores a single data object

    This also stores the encoder for any cloud object so
    we can encode it.
    """

    Encoder = CloudDataEncoder

    def __init__(self, items):
        self.data = items
        self.lookup = {}
        self.create_lookup()

    def create_lookup(self):
        """
        If we have a name attribute and a list of data, cache a lookup for later
        """
        if not (hasattr(self, "name_attribute") and isinstance(self.data, list)):
            return
        key = self.name_attribute
        for item in self.data:
            if key not in item:
                continue
            self.lookup[item[key]] = item


class Instance(CloudData):
    """
    Base of an instance.

    This class defines the different common attributes that we want
    to expose. If a cloud instance (json) result differs, it should
    override this function.
    """

    @property
    def attribute_getters(self):
        """
        function names we can call to get an instance attribute.
        """
        fields = []
        for func in dir(self):
            if func.startswith("attr_"):
                fields.append(func)
        return fields

    # Attributes shared between clouds (maybe)
    def attr_description(self):
        return self.data.get("description")

    def attr_zone(self):
        return self.data.get("zone")

    @property
    def name(self):
        return self.data.get("name")

    def generate_row(self, name):
        """
        Given an instance name, return a row with the cloud
        name and other attributes.
        """
        raise NotImplementedError


class InstanceGroup(CloudData):
    """
    A cloud instance group.

    An instance group stores raw data, and allows for query or
    other interaction over instances.
    """

    # If we don't have an instance class, return as dict
    Instance = dict

    def generate_row(self, name):
        """
        Given an instance name, return a row with the cloud
        name and other attributes.
        """
        # We assume that we have the item in the lookup
        if name not in self.lookup:
            raise ValueError(f"{name} is not known to {self}")
        return self.Instance(self.lookup[name]).generate_row()

    def iter_instances(self):
        """
        Each client knows how to instantiate its instance type
        """
        for item in self.data:
            yield self.Instance(item)


class Prices(CloudData):
    """
    Cloud pricing
    """

    pass
