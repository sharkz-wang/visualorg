# -*- coding: utf-8 -*-

from PyOrgMode.PyOrgMode import OrgDataStructure
from PyOrgMode.PyOrgMode import OrgDrawer
from PyOrgMode.PyOrgMode import OrgElement
from datetime import datetime
import json
import time
import math
from pprint import pprint
from Queue import Queue
from jinja2 import Template

hide_hidden_tasks = True

project_subtree_tag = 'Project'
milestone_tag = 'Milestone'
archived_tag = 'Archived'
hidden_tag = 'Hidden'

base = OrgDataStructure()
base.set_todo_states(['TODO', 'STARTED', 'WAITING', 'SCHEDULED',
                      '|',
                      'DONE', 'ABORTED', 'SUSPENDED'])
base.load_from_file('../inbox.org')
root = base.root

is_node = lambda x: isinstance(x, OrgElement) and 'heading' in x.__dict__

def tree2dict(root, get_nodes, project_subtree=False, gantt_level=0):

    ret_mindmap = dict()
    ret_todo_list = []
    ret_gantt = []
    ret_timeline = {
        'events': [],
        'legends': []
    }

    project_subtree = project_subtree or project_subtree_tag in root.tags
    is_project = project_subtree_tag in root.tags
    is_milestone = milestone_tag in root.tags
    is_archived = archived_tag in root.tags
    is_hidden = hidden_tag in root.tags

    if is_archived or (hide_hidden_tasks and is_hidden):
        return (ret_mindmap, ret_todo_list, ret_gantt, ret_timeline)

    # chomp trailing whitespaces
    root.heading = root.heading.rstrip()

    start_ts_ms = None
    end_ts_ms = None

    if len(root.content) > 0 and hasattr(root.content[0], 'scheduled'):
        start_ts_ms = int(time.mktime(root.content[0].scheduled.value) * 1000)
    if len(root.content) > 0 and hasattr(root.content[0], 'deadline'):
        end_ts_ms = int(time.mktime(root.content[0].deadline.value) * 1000)

    # init property info of root node of current subtree
    property_nodes = []
    root_properties = []
    node_id = None
    dep_id = None

    # get first property node
    if hasattr(root, 'content'):
        # import pdb; pdb.set_trace()
        property_nodes = filter(lambda x: hasattr(x, 'content') and\
                                isinstance(x.content, list) and\
                                len(x.content) > 0 and\
                                isinstance(x.content[0], OrgDrawer.Property),
                                root.content)
    if property_nodes:
        root_properties = property_nodes[0]
        # get CUSTOM_ID and DEPENDENCY
        for prop in root_properties.content:
            if prop.name == 'CUSTOM_ID':
                node_id = prop.value
            if prop.name == 'DEPENDENCY':
                dep_id = prop.value

    ret_mindmap['name'] = root.heading

    if project_subtree_tag in root.tags or\
       (project_subtree and (start_ts_ms or end_ts_ms)):

        start_is_milestone = False
        end_is_milestone = False
        duration = None

        if project_subtree_tag in root.tags:
            # TODO: use magic date for dummy gantt items, fix this ugly hack
            start_ts_ms = 1893455999000
            end_ts_ms = 1893455999000
        else:
            if not start_ts_ms and end_ts_ms:
                start_ts_ms = end_ts_ms
                end_is_milestone = True
            if start_ts_ms and not end_ts_ms:
                end_ts_ms = start_ts_ms
                start_is_milestone = True

            ms_per_day = 24*60*60*1000
            duration_date_ts_list = range(start_ts_ms, end_ts_ms + ms_per_day, ms_per_day)
            duration_date_list = map(lambda x: datetime.fromtimestamp(x/1000), duration_date_ts_list)
            duration_weekday_list = map(lambda x: x.weekday(), duration_date_list)

            # twproject gantt ignores weekends when counting duration
            duration = len(filter(lambda x: x < 5, duration_weekday_list))

        ret_gantt.append({
            "id": node_id,
            "name": root.heading,
            "progress": 0,
            "progressByWorklog": False,
            "relevance": 0,
            "type": "",
            "typeId": "",
            "description": "",
            "code": "",
            "level": gantt_level,
            "status": "STATUS_ACTIVE",
            "depends": dep_id if dep_id else "",
            "canWrite": True,
            "start": (start_ts_ms if start_ts_ms else ""),
            "end": (end_ts_ms if end_ts_ms else ""),
            "duration": (duration if duration else 1),
            "startIsMilestone": start_is_milestone,
            "endIsMilestone": end_is_milestone,
            "collapsed": False,
            "assigs": [],
            "hasChild": True
            })

        gantt_level += 1

        if is_project or is_milestone:
            ret_timeline['events'].append({
                "id": node_id,
                "title": root.heading if not is_project else root.heading + ' done',
                "description": "",
                "startdate": (datetime.fromtimestamp(start_ts_ms/1000).strftime('%Y-%m-%d %H:%M:%S')
                            if start_ts_ms and not is_project
                              else datetime.fromtimestamp(end_ts_ms/1000).strftime('%Y-%m-%d %H:%M:%S')),
                "enddate": (datetime.fromtimestamp(end_ts_ms/1000).strftime('%Y-%m-%d %H:%M:%S')
                            if end_ts_ms
                            else ""),
                "high_threshold": 50,
                "importance": "30",
                "image": "",
                "link": "",
                "date_display": "yes",
                "icon": "triangle_green.png" if not is_project else "flag_red.png",
                "tags": ""
                })


    if hasattr(root, 'todo'):
        if root.todo == 'SCHEDULED':
            ret_todo = dict()
            ret_todo['status'] = root.todo
            ret_todo['heading'] = root.heading
            ret_todo_list.append(ret_todo)

        ret_mindmap['todo'] = root.todo
        ret_mindmap['name'] = "[" + root.todo.lower() + "] " + ret_mindmap['name']

    # if hasattr(root, 'todo'):
    #     return ret_mindmap

    ret_mindmap['children'] = []

    for node in get_nodes(root):
        (_mdmp, _todo_lsit, _gantt_list, _timeline) = tree2dict(node,
                                                                get_nodes,
                                                                project_subtree,
                                                                gantt_level)
        ret_gantt = ret_gantt + _gantt_list

        ret_todo_list = ret_todo_list + _todo_lsit
        if _mdmp:
            ret_mindmap['children'].append(_mdmp)

        ret_timeline['events'] = _timeline['events'] + ret_timeline['events']

    if not ret_mindmap['children']:
        del ret_mindmap['children']

    return (ret_mindmap, ret_todo_list, ret_gantt, ret_timeline)

root.heading = '/'
(mindmap, todo, gantt, timeline) = tree2dict(root, lambda n: filter(is_node, n.content))

custom_gantt_id_map_tb = dict()

# convert CUSTOM_IDs into twproject gantt's relative ids (i.e., -1, -2, -3 ...)
for en in enumerate(gantt):
    idx = -(en[0] + 1)
    gantt_item = en[1]
    custom_gantt_id_map_tb[gantt_item['id']] = idx

for en in enumerate(gantt):
    idx = -(en[0] + 1)
    gantt_item = en[1]
    gantt_item['id'] = idx
    if gantt_item['depends']:
        gantt_item['depends'] = "%d" % -custom_gantt_id_map_tb[gantt_item['depends']]

tmpl_f = open('test_bootstrap.html')
tmpl_txt = tmpl_f.read()

tmpl = Template(tmpl_txt.decode('utf-8'))
result = tmpl.render(mindmap_json=('[' + json.dumps(mindmap, ensure_ascii=False) + "]").decode('utf-8'),
                     todo_json=json.dumps(todo, ensure_ascii=False).decode('utf-8'))

out_f = open('mindmap.html', 'w')
out_f.write(result.encode('utf-8'))

tmpl_f.close()
out_f.close()

tmpl_f = open('./twproject_gantt/gantt_tmpl.html')
tmpl_txt = tmpl_f.read()

tmpl = Template(tmpl_txt.decode('utf-8'))
result = tmpl.render(gantt_json=json.dumps(gantt, ensure_ascii=False).decode('utf-8'))

out_f = open('./twproject_gantt/gantt.html', 'w')
out_f.write(result.encode('utf-8'))

tmpl_f.close()
out_f.close()

tmpl_f = open('./timeglider/full_window_tmpl.html')
tmpl_txt = tmpl_f.read()

tmpl = Template(tmpl_txt.decode('utf-8'))
result = tmpl.render(timeline_events=json.dumps(timeline['events'], ensure_ascii=False).decode('utf-8'))

out_f = open('./timeglider/full_window.html', 'w')
out_f.write(result.encode('utf-8'))

tmpl_f.close()
out_f.close()
