# -*- coding: utf-8 -*-

from PyOrgMode.PyOrgMode import OrgDataStructure
from PyOrgMode.PyOrgMode import OrgDrawer
from PyOrgMode.PyOrgMode import OrgElement
import re
from datetime import datetime, timedelta
import json
import time
import math
from pprint import pprint
from Queue import Queue
from jinja2 import Template

hide_hidden_tasks = True
hide_done_tasks = True
enable_default_folding = True

project_subtree_tag = 'Project'
milestone_tag = 'Milestone'
archived_tag = 'Archived'
hidden_tag = 'Hidden'
folded_subtree_tag = 'Folded'

todo_keyword_list = [ 'TODO', 'STARTED', 'WAITING', 'SCHEDULED' ]
done_keyword_list = [ 'DONE', 'ABORTED', 'SUSPENDED' ]

base = OrgDataStructure()
base.set_todo_states(todo_keyword_list + [ '|' ] + done_keyword_list)
base.load_from_file('../inbox.org')
root = base.root

is_node = lambda x: isinstance(x, OrgElement) and 'heading' in x.__dict__

def get_state_change_ts(state, content):

    ret_ts = None
    pattern = r'\s*?-\s+State\s+"%s".*?\[(.*?)\]' % state

    for item in filter(lambda x: isinstance(x, str), content):
        matched = re.match(pattern, item)
        if matched:
            org_date_str = matched.group(1)
            ret_ts = time.mktime(datetime.strptime(org_date_str, "%Y-%m-%d %a %H:%M").timetuple()) * 1000

    return ret_ts

def tree2dict(root, get_nodes, project_subtree=False, project=None, gantt_level=0):

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
    is_folded = folded_subtree_tag in root.tags
    is_done = hasattr(root, 'todo') and root.todo in done_keyword_list

    if is_archived or (hide_hidden_tasks and is_hidden):
        return (ret_mindmap, ret_todo_list, ret_gantt, ret_timeline)

    # chomp trailing whitespaces
    root.heading = root.heading.rstrip()

    if is_project:
        project = root.heading

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
    dep_id = []

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
                dep_id.append(prop.value)

    ret_mindmap['name'] = root.heading

    if project_subtree_tag in root.tags or\
       (project_subtree and (start_ts_ms or end_ts_ms)):

        start_is_milestone = False
        end_is_milestone = False
        duration = None

        if project_subtree_tag in root.tags:
            start_ts_ms = None
            end_ts_ms = None
        else:
            if not start_ts_ms and end_ts_ms:
                start_ts_ms = end_ts_ms
                end_is_milestone = True
            if start_ts_ms and not end_ts_ms:
                end_ts_ms = start_ts_ms
                start_is_milestone = True

            ms_per_day = 24*60*60*1000
            duration = len(range(start_ts_ms, end_ts_ms + ms_per_day, ms_per_day))

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
            "depends": dep_id,
            "canWrite": True,
            "start": (start_ts_ms if start_ts_ms else ""),
            "end": (end_ts_ms if end_ts_ms else ""),
            "duration": (duration if duration else "--"),
            "startIsMilestone": start_is_milestone,
            "endIsMilestone": end_is_milestone,
            "collapsed": False,
            "assigs": [],
            "hasChild": True
            })

        gantt_level += 1

        if (is_project or is_milestone) and (start_ts_ms or end_ts_ms):
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
        ret_todo = dict()
        ret_todo['state'] = root.todo
        ret_todo['milestone'] = project if project else ""
        ret_todo['name'] = root.heading
        ret_todo['task_type'] = root.tags if root.tags else "None"
        ret_todo['description'] = 'no description'

        date_ts = None
        date_str = None

        if ret_todo['state'] == 'DONE':
            date_ts = get_state_change_ts(ret_todo['state'], root.content) // 1000
            date_str = datetime.fromtimestamp(date_ts).strftime('%-m/%d %a %H:%M')

        elif ret_todo['state'] == 'WAITING':
            date_ts = get_state_change_ts(ret_todo['state'], root.content) // 1000

            abs_date = datetime.fromtimestamp(date_ts).strftime('%-m/%d %a %H:%M')

            curr_ts = int(time.time())
            delta = datetime(1, 1, 1) + timedelta(seconds=curr_ts - date_ts)
            rel_date = "~ %d days %d hrs" % (delta.day-1, delta.hour)

            date_str = rel_date + "\n" + abs_date

        elif ret_todo['state'] == 'STARTED':
            date_ts = get_state_change_ts(ret_todo['state'], root.content) // 1000

            curr_ts = int(time.time())
            delta = datetime(1, 1, 1) + timedelta(seconds=curr_ts - date_ts)
            rel_date = "~ %d days %d hrs" % (delta.day-1, delta.hour)

            date_str = rel_date

        ret_todo['date_ts'] = date_ts
        ret_todo['date_str'] = date_str

        ret_todo_list.append(ret_todo)

        ret_mindmap['todo'] = root.todo
        ret_mindmap['name'] = "[" + root.todo.lower() + "] " + ret_mindmap['name']

    # if hasattr(root, 'todo'):
    #     return ret_mindmap

    ret_mindmap['children'] = []
    ret_mindmap['_children'] = []

    for node in get_nodes(root):
        (_mdmp, _todo_lsit, _gantt_list, _timeline) = tree2dict(node,
                                                                get_nodes,
                                                                project_subtree,
                                                                project,
                                                                gantt_level)
        ret_gantt = ret_gantt + _gantt_list

        ret_todo_list = ret_todo_list + _todo_lsit
        if _mdmp:
            if is_folded and enable_default_folding:
                ret_mindmap['_children'].append(_mdmp)
            else:
                ret_mindmap['children'].append(_mdmp)

        ret_timeline['events'] = _timeline['events'] + ret_timeline['events']

    if not ret_mindmap['children']:
        del ret_mindmap['children']

    if not ret_mindmap['_children']:
        del ret_mindmap['_children']

    if hide_done_tasks and is_done:
        ret_mindmap = dict()

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
        dep_list = map(lambda x: -custom_gantt_id_map_tb[x], gantt_item['depends'])
        dep_str_list = map(lambda x: "%d" % x, dep_list)
        gantt_item['depends'] = ",".join(dep_str_list)
    else:
        gantt_item['depends'] = None

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

tmpl_f = open('./kanban/index_tmpl.html')
tmpl_txt = tmpl_f.read()

has_done_date = lambda task: task['state'] == 'DONE' and 'date_ts' in task
done_tasks = filter(has_done_date, todo)
other_tasks = filter(lambda task: not has_done_date(task), todo)

done_tasks_sorted_desc = sorted(done_tasks, key=lambda task: task['date_ts'], reverse=True)

todo = done_tasks_sorted_desc + other_tasks

tmpl = Template(tmpl_txt.decode('utf-8'))
result = tmpl.render(task_list=json.dumps(todo, ensure_ascii=False).decode('utf-8'))

out_f = open('./kanban/index.html', 'w')
out_f.write(result.encode('utf-8'))

tmpl_f.close()
out_f.close()
