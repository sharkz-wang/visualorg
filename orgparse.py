# -*- coding: utf-8 -*-

from PyOrgMode.PyOrgMode import OrgDataStructure
from PyOrgMode.PyOrgMode import OrgDrawer
from PyOrgMode.PyOrgMode import OrgElement
import json
import time
import math
from pprint import pprint
from Queue import Queue
from jinja2 import Template

project_subtree_tag = 'Project'

base = OrgDataStructure()
base.set_todo_states(['TODO', 'STARTED', 'WAITING', 'SCHEDULED',
                      '|',
                      'DONE', 'ABORTED', 'SUSPENDED'])
base.load_from_file('./inbox.org')
root = base.root

is_node = lambda x: isinstance(x, OrgElement) and 'heading' in x.__dict__

def tree2dict(root, get_nodes, project_subtree=False):

    project_subtree = project_subtree or project_subtree_tag in root.tags

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

    ret_mindmap = dict()
    ret_todo_list = []
    ret_gantt = []

    ret_mindmap['name'] = root.heading

    if project_subtree and (start_ts_ms or end_ts_ms):

        end_is_milestone = False
        if not start_ts_ms and end_ts_ms:
            start_ts_ms = end_ts_ms
            end_is_milestone = True
        if start_ts_ms and not end_ts_ms:
            end_ts_ms = start_ts_ms
            end_is_milestone = True

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
            "level": 0,
            "status": "STATUS_ACTIVE",
            "depends": dep_id if dep_id else "",
            "canWrite": True,
            "start": (start_ts_ms if start_ts_ms else ""),
            "end": (end_ts_ms if end_ts_ms else ""),
            "duration": (math.ceil((end_ts_ms - start_ts_ms)/1000/60/60/24)
                         if start_ts_ms and end_ts_ms else
                         0),
            "startIsMilestone": False,
            "endIsMilestone": False,
            "collapsed": False,
            "assigs": [],
            "hasChild": True
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
        (_mdmp, _todo_lsit, _gantt_list) = tree2dict(node,
                                                     get_nodes,
                                                     project_subtree)
        if project_subtree:
            for it in enumerate(_gantt_list):
                idx = it[0]
                item = it[1]

                item['level'] += 1
        ret_gantt = ret_gantt + _gantt_list

        ret_todo_list = ret_todo_list + _todo_lsit
        ret_mindmap['children'].append(_mdmp)

    if not ret_mindmap['children']:
        del ret_mindmap['children']

    return (ret_mindmap, ret_todo_list, ret_gantt)

root.heading = '/'
(mindmap, todo, gantt) = tree2dict(root, lambda n: filter(is_node, n.content))

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

out_f = open('out.html', 'w')
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
