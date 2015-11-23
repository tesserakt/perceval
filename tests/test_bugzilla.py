#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#


import datetime
import sys
import unittest

import httpretty

if not '..' in sys.path:
    sys.path.insert(0, '..')

from perceval.errors import ParseError
from perceval.backends.bugzilla import Bugzilla, BugzillaClient


BUGZILLA_SERVER_URL = 'http://example.com'
BUGZILLA_METADATA_URL = BUGZILLA_SERVER_URL + '/show_bug.cgi'
BUGZILLA_BUGLIST_URL = BUGZILLA_SERVER_URL + '/buglist.cgi'
BUGZILLA_BUG_URL = BUGZILLA_SERVER_URL + '/show_bug.cgi'
BUGZILLA_BUG_ACTIVITY_URL = BUGZILLA_SERVER_URL + '/show_activity.cgi'


def read_file(filename, mode='r'):
    with open(filename, mode) as f:
        content = f.read()
    return content


class TestBugzillaBackend(unittest.TestCase):
    """Bugzilla backend tests"""

    @httpretty.activate
    def test_fetch(self):
        """Test whether a list of bugs is returned"""

        requests = []
        bodies_csv = [read_file('data/bugzilla_buglist.csv'),
                      read_file('data/bugzilla_buglist_next.csv'),
                      ""]
        bodies_xml = [read_file('data/bugzilla_bugs_details.xml', mode='rb'),
                      read_file('data/bugzilla_bugs_details_next.xml', mode='rb')]

        def request_callback(method, uri, headers):
            requests.append(httpretty.last_request())

            if uri.startswith(BUGZILLA_BUGLIST_URL):
                body = bodies_csv.pop(0)
            else:
                body = bodies_xml.pop(0)
            return (200, headers, body)

        httpretty.register_uri(httpretty.GET, BUGZILLA_BUGLIST_URL,
                               responses=[
                                    httpretty.Response(body=request_callback),
                                    httpretty.Response(body=request_callback),
                                    httpretty.Response(body=request_callback)
                               ])
        httpretty.register_uri(httpretty.GET, BUGZILLA_BUG_URL,
                               responses=[
                                    httpretty.Response(body=request_callback),
                                    httpretty.Response(body=request_callback)
                               ])

        bg = Bugzilla(BUGZILLA_SERVER_URL, max_bugs=5)
        bugs = [bug for bug in bg.fetch()]

        self.assertEqual(len(bugs), 7)
        self.assertEqual(bugs[0]['bug_id'][0]['__text__'], '15')
        self.assertEqual(bugs[6]['bug_id'][0]['__text__'], '888')

        # Check requests
        expected = [{
                     'ctype' : ['csv'],
                     'order' : ['changeddate'],
                     'chfieldfrom' : ['1970-01-01T00:00:00']
                    },
                    {
                     'ctype' : ['csv'],
                     'order' : ['changeddate'],
                     'chfieldfrom' : ['2009-07-30T11:35:33']
                    },
                    {
                     'ctype' : ['csv'],
                     'order' : ['changeddate'],
                     'chfieldfrom' : ['2015-08-12T18:32:11']
                    },
                    {
                     'ctype' : ['xml'],
                     'id' : ['15', '18', '17', '20', '19'],
                     'excludefield' : ['attachmentdata']
                    },
                    {
                     'ctype' : ['xml'],
                     'id' : ['30', '888'],
                     'excludefield' : ['attachmentdata']
                    },]

        self.assertEqual(len(requests), 5)

        for i in range(len(expected)):
            self.assertDictEqual(requests[i].querystring, expected[i])

    @httpretty.activate
    def test_fetch_from_date(self):
        """Test whether a list of bugs is returned from a given date"""

        requests = []
        bodies_csv = [read_file('data/bugzilla_buglist_next.csv'),
                      ""]
        bodies_xml = [read_file('data/bugzilla_bugs_details_next.xml', mode='rb')]

        def request_callback(method, uri, headers):
            requests.append(httpretty.last_request())

            if uri.startswith(BUGZILLA_BUGLIST_URL):
                body = bodies_csv.pop(0)
            else:
                body = bodies_xml.pop(0)
            return (200, headers, body)

        httpretty.register_uri(httpretty.GET, BUGZILLA_BUGLIST_URL,
                               responses=[
                                    httpretty.Response(body=request_callback),
                                    httpretty.Response(body=request_callback),
                               ])
        httpretty.register_uri(httpretty.GET, BUGZILLA_BUG_URL,
                               responses=[
                                    httpretty.Response(body=request_callback)
                               ])

        from_date = datetime.datetime(2015, 1, 1)

        bg = Bugzilla(BUGZILLA_SERVER_URL)
        bugs = [bug for bug in bg.fetch(from_date=from_date)]

        self.assertEqual(len(bugs), 2)
        self.assertEqual(bugs[0]['bug_id'][0]['__text__'], '30')
        self.assertEqual(bugs[1]['bug_id'][0]['__text__'], '888')

        # Check requests
        expected = [{
                     'ctype' : ['csv'],
                     'order' : ['changeddate'],
                     'chfieldfrom' : ['2015-01-01T00:00:00']
                    },
                    {
                     'ctype' : ['csv'],
                     'order' : ['changeddate'],
                     'chfieldfrom' : ['2015-08-12T18:32:11']
                    },
                    {
                     'ctype' : ['xml'],
                     'id' : ['30', '888'],
                     'excludefield' : ['attachmentdata']
                    },]

        self.assertEqual(len(requests), 3)

        for i in range(len(expected)):
            self.assertDictEqual(requests[i].querystring, expected[i])

    @httpretty.activate
    def test_fetch_empty(self):
        """Test whethet it works when no bugs are fetched"""

        httpretty.register_uri(httpretty.GET, BUGZILLA_BUGLIST_URL,
                               body="", status=200)

        from_date = datetime.datetime(2100, 1, 1)


        bg = Bugzilla(BUGZILLA_SERVER_URL)
        bugs = [bug for bug in bg.fetch(from_date=from_date)]

        self.assertEqual(len(bugs), 0)

        # Check request
        expected = {
                     'ctype' : ['csv'],
                     'order' : ['changeddate'],
                     'chfieldfrom' : ['2100-01-01T00:00:00']
                    }

        req = httpretty.last_request()

        self.assertDictEqual(req.querystring, expected)

    def test_parse_buglist(self):
        """Test buglist parsing"""

        raw_csv = read_file('data/bugzilla_buglist.csv')

        bugs = Bugzilla.parse_buglist(raw_csv)
        result = [bug for bug in bugs]

        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]['bug_id'], '15')
        self.assertEqual(result[4]['bug_id'], '19')

    def test_parse_bugs_details(self):
        """Test bugs details parsing"""

        raw_xml = read_file('data/bugzilla_bugs_details.xml')

        bugs = Bugzilla.parse_bugs_details(raw_xml)
        result = [bug for bug in bugs]

        self.assertEqual(len(result), 5)

        bug_ids = [bug['bug_id'][0]['__text__'] \
                   for bug in result]
        expected = ['15', '18', '17', '20', '19']

        self.assertListEqual(bug_ids, expected)

        raw_xml = read_file('data/bugzilla_bugs_details_next.xml')

        bugs = Bugzilla.parse_bugs_details(raw_xml)
        result = [bug for bug in bugs]

    def test_parse_invalid_bug_details(self):
        """Test whether it fails parsing an invalid XML with no bugs"""

        raw_xml = read_file('data/bugzilla_bugs_details_not_valid.xml')

        with self.assertRaises(ParseError):
            bugs = Bugzilla.parse_bugs_details(raw_xml)
            _ = [bug for bug in bugs]

    def test_parse_activity(self):
        """Test activity bug parsing"""

        raw_html = read_file('data/bugzilla_bug_activity.html')

        activity = Bugzilla.parse_bug_activity(raw_html)
        result = [event for event in activity]

        self.assertEqual(14, len(result))

        expected = {
                    'Who' : 'sduenas@example.org',
                    'When' : '2013-06-25 11:57:23 CEST',
                    'What' : 'Attachment #172 Attachment is obsolete',
                    'Removed' : '0',
                    'Added' : '1'
                   }
        self.assertDictEqual(result[0], expected)

        expected = {
                    'Who' : 'sduenas@example.org',
                    'When' : '2013-06-25 11:59:07 CEST',
                    'What' : 'Depends on',
                    'Removed' : '350',
                    'Added' : ''
                   }
        self.assertDictEqual(result[6], expected)

    def test_parse_empty_activity(self):
        """Test the parser when the activity table is empty"""

        raw_html = read_file('data/bugzilla_bug_activity_empty.html')

        activity = Bugzilla.parse_bug_activity(raw_html)
        result = [event for event in activity]
        self.assertEqual(len(result), 0)

    def test_parse_activity_no_table(self):
        """Test if it raises an exception the activity table is not found"""

        raw_html = read_file('data/bugzilla_bug_activity_not_valid.html')

        with self.assertRaises(ParseError):
            activity = Bugzilla.parse_bug_activity(raw_html)
            _ = [event for event in activity]


class TestBugzillaClient(unittest.TestCase):
    """Bugzilla API client tests

    These tests not check the body of the response, only if the call
    was well formed and if a response was obtained. Due to this, take
    into account that the body returned on each request might not
    match with the parameters from the request.
    """
    @httpretty.activate
    def test_metadata(self):
        """Test metadata API call"""

        # Set up a mock HTTP server
        body = read_file('data/bugzilla_version.xml')

        httpretty.register_uri(httpretty.GET,
                               BUGZILLA_METADATA_URL,
                               body=body, status=200)

        # Call API
        client = BugzillaClient(BUGZILLA_SERVER_URL)
        response = client.metadata()

        self.assertEqual(response, body)

        # Check request params
        expected = {'ctype' : ['xml']}

        req = httpretty.last_request()

        self.assertEqual(req.method, 'GET')
        self.assertRegex(req.path, '/show_bug.cgi')
        self.assertDictEqual(req.querystring, expected)

    @httpretty.activate
    def test_buglist(self):
        """Test buglist API call"""

        # Set up a mock HTTP server
        body = read_file('data/bugzilla_buglist.csv')

        httpretty.register_uri(httpretty.GET,
                               BUGZILLA_BUGLIST_URL,
                               body=body, status=200)

        # Call API without args
        client = BugzillaClient(BUGZILLA_SERVER_URL)
        response = client.buglist()

        self.assertEqual(response, body)

        # Check request params
        expected = {
                    'ctype' : ['csv'],
                    'order' : ['changeddate'],
                    'chfieldfrom' : ['1970-01-01T00:00:00']
                   }

        req = httpretty.last_request()

        self.assertEqual(req.method, 'GET')
        self.assertRegex(req.path, '/buglist.cgi')
        self.assertDictEqual(req.querystring, expected)

        # Call API with from_date and version args
        response = client.buglist(from_date=datetime.datetime(2015, 1, 1),
                                  version='4.0')

        self.assertEqual(response, body)

        # Check request params
        expected = {
                    'ctype' : ['csv'],
                    'order' : ['changeddate'],
                    'chfieldfrom' : ['2015-01-01T00:00:00']
                   }

        req = httpretty.last_request()

        self.assertEqual(req.method, 'GET')
        self.assertRegex(req.path, '/buglist.cgi')
        self.assertDictEqual(req.querystring, expected)

    @httpretty.activate
    def test_buglist_old_version(self):
        """Test buglist API call when the version of the server is less than 3.3"""

        # Set up a mock HTTP server
        body = read_file('data/bugzilla_buglist.csv')

        httpretty.register_uri(httpretty.GET,
                               BUGZILLA_BUGLIST_URL,
                               body=body, status=200)

        # Call API without args
        client = BugzillaClient(BUGZILLA_SERVER_URL)
        response = client.buglist(version='3.2.3')

        self.assertEqual(response, body)

        # Check request params
        expected = {
                    'ctype' : ['csv'],
                    'order' : ['Last Changed'],
                    'chfieldfrom' : ['1970-01-01T00:00:00']
                    }

        req = httpretty.last_request()

        self.assertEqual(req.method, 'GET')
        self.assertRegex(req.path, '/buglist.cgi')
        self.assertDictEqual(req.querystring, expected)

    @httpretty.activate
    def test_bugs(self):
        """Test bugs API call"""

        # Set up a mock HTTP server
        body = read_file('data/bugzilla_bug.xml')

        httpretty.register_uri(httpretty.GET,
                               BUGZILLA_BUG_URL,
                               body=body, status=200)

        # Call API
        client = BugzillaClient(BUGZILLA_SERVER_URL)
        response = client.bugs('8', '9')

        self.assertEqual(response, body)

        # Check request params
        expected = {
                    'id' : ['8', '9'],
                    'ctype' : ['xml'],
                    'excludefield' : ['attachmentdata']
                   }

        req = httpretty.last_request()

        self.assertEqual(req.method, 'GET')
        self.assertRegex(req.path, '/show_bug.cgi')
        self.assertDictEqual(req.querystring, expected)

    @httpretty.activate
    def test_bug_activity(self):
        """Test bug acitivity API call"""

        # Set up a mock HTTP server
        body = read_file('data/bugzilla_bug_activity.html')

        httpretty.register_uri(httpretty.GET,
                               BUGZILLA_BUG_ACTIVITY_URL,
                               body=body, status=200)

        # Call API
        client = BugzillaClient(BUGZILLA_SERVER_URL)
        response = client.bug_activity('8')

        self.assertEqual(response, body)

        # Check request params
        expected = {'id' : ['8']}

        req = httpretty.last_request()

        self.assertEqual(req.method, 'GET')
        self.assertRegex(req.path, '/show_activity.cgi')
        self.assertDictEqual(req.querystring, expected)


if __name__ == "__main__":
    unittest.main()