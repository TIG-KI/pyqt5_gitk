import sys
from sys import argv
from os import listdir, path
from queue import Queue
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt, QPoint

class git_action:
        def __init__(self, action_parent, action_sha, action_user, action_time, action_message):
                self.parent_sha = action_parent
                self.sha = action_sha
                self.user = action_user
                self.time = action_time
                self.action = action_message.split(':')[0]
                self.message = action_message.split(':')[1].strip()
                self.children = []
                self.branch = None

        def __str__(self):
                return ' | '.join([self.parent_sha, self.sha, self.user, self.time, self.action, self.message])

        def get_color(self):
                qcolor = QColor(0, 0, 0)
                if self.action == 'branch':
                        qcolor = QColor(100, 255, 100)
                elif 'rebase' in self.action:
                        qcolor = QColor(100, 100, 255)
                elif 'amend' in self.action:
                        qcolor = QColor(150, 150, 150)
                return qcolor


class git_branch:
        def __init__(self, branch_name, action_list):
                self.name = branch_name
                self.action_list = action_list
                for ai in self.action_list:
                        ai.branch = self
                self.action_queue = None
                self.make_actions()

        def __str__(self):
                return self.name

        def get_actions(self):
                return '\n'.join([self.name + ' -> ' + str(action) for action in self.action_list])

        def make_actions(self):
                for action in self.action_list:
                        if self.action_queue is None:
                                self.action_queue = action
                        else:
                                found = False
                                node_queue = Queue()
                                node_queue.put(self.action_queue)
                                while not node_queue.empty():
                                        node = node_queue.get()
                                        if node.sha == action.parent_sha:
                                                node.children += [action]
                                                found = True
                                                break
                                        else:
                                                for cc in node.children:
                                                        node_queue.put(cc)

        def get_colors(self):
                color = 1
                for c in self.name:
                        color = (color*ord(c)) % (256*256*256)
                rgb = [0, 0, 0]
                hvi = 0
                for i in range(3):
                        c = color % 256
                        if c < 100:
                                c += 100
                        rgb[(len(self.name) + i) % 3] = c
                        if rgb[hvi] < c:
                                hvi = (len(self.name) + i) % 3
                        color //= 256
                pen_rgb = [[int(rgb[i]*0.25), rgb[i]][hvi == i] for i in range(3)]
                return (QColor(pen_rgb[0], pen_rgb[1], pen_rgb[2]), QColor(rgb[0], rgb[1], rgb[2]))


class git_tree:
        def __init__(self, branches):
                self.branches = branches
                self.roots = None
                self.merge_branches()

        def __getitem__(self, key):
                for branch in self.branches:
                        if branch.name == key:
                                return branch
                return None

        def __str__(self):
                return '\n'.join([str(branch) for branch in self.branches])

        def merge_branches(self):
                self.roots = [b.action_queue for b in self.branches]
                excluded_roots = []
                for root in self.roots:
                        found = False
                        for root2 in self.roots:
                                if root.sha == root2.sha and root.parent_sha == root2.parent_sha:
                                        continue
                                node_queue = Queue()
                                node_queue.put(root2)
                                while not found and not node_queue.empty():
                                        node = node_queue.get()
                                        if node.sha == root.sha:
                                                node.children += [root]
                                                found = True
                                                break
                                        else:
                                                for cc in node.children:
                                                        node_queue.put(cc)
                                if found:
                                        break
                        if found:
                                excluded_roots += [root]
                for eroot in excluded_roots:
                        self.roots.remove(eroot)


class tree_window(QWidget):
        def __init__(self, git_tree):
                super().__init__()
                self.initUI()
                self.git_tree = git_tree

        def initUI(self):
                self.setGeometry(100, 100, 900, 500)
                self.setWindowTitle('GITK')
                self.show()

        def paintEvent(self, e):
                qp = QPainter()
                qp.begin(self)
                self.draw_git_tree(qp)

        def draw_git_tree(self, qp):
                action_matrix = [[]]
                roots = self.git_tree.roots
                for root in roots:
                        q = Queue()
                        q.put(root)
                        while not q.empty():
                                found = False
                                curr_node = q.get()
                                for r in range(len(action_matrix)):
                                        if (curr_node.parent_sha, curr_node.branch.name) in [(a[0].sha, a[0].branch.name) for a in action_matrix[r] if not a is None]:
                                                action_matrix[r] += [(curr_node, r - 1)]
                                                found = True
                                                break
                                        elif curr_node.action == 'branch' and curr_node.sha in [a[0].sha for a in action_matrix[r] if not a is None]:
                                                pos = sum([0] + [None for a in action_matrix[r] if a is None])
                                                pos += [a[0].sha for a in action_matrix[r] if not a is None].index(curr_node.sha)
                                                action_matrix += [[None]*pos + [(curr_node, r - 1)]]
                                                found = True
                                                break
                                if not found:
                                        action_matrix += [[(curr_node, 0)]]
                                for c in curr_node.children:
                                        q.put(c)
                        action_matrix += [[]]
                action_matrix = action_matrix[1:-1]
                for r in range(len(action_matrix)):
                        for c in range(len(action_matrix[r])):
                                if action_matrix[r][c] is None:
                                        continue
                                else:
                                        colors = action_matrix[r][c][0].branch.get_colors()
                                        qp.setPen(colors[0])
                                        qp.setBrush(colors[1])
                                        qp.drawRect(c*100 + 50, r*100 + 50, 50, 50)

                                        qp.setPen(action_matrix[r][c][0].get_color())
                                        if r == c == 0:
                                                continue
                                        elif action_matrix[r][c][0].action == 'branch':
                                                qp.drawLine(QPoint(c*100 + 50, action_matrix[r][c][1]*100 + 90), QPoint(c*100 + 25, action_matrix[r][c][1]*100 + 90))
                                                qp.drawLine(QPoint(c*100 + 50, r*100 + 60), QPoint(c*100 + 25, r*100 + 60))
                                                qp.drawLine(QPoint(c*100 + 25, action_matrix[r][c][1]*100 + 90), QPoint(c*100 + 25, r*100 + 60))
                                        elif 'commit' in action_matrix[r][c][0].action:
                                                qp.drawLine(QPoint(c*100 + 50, action_matrix[r][c][1]*100 + 75), QPoint(c*100, action_matrix[r][c][1]*100 + 75))



def get_git_path(dir_path):
        if '.git' in listdir(dir_path):
                return path.join(dir_path, '.git')
        return None


def get_git_branches(git_path):
        return listdir(path.join(git_path, 'logs', 'refs', 'heads'))


if __name__ == '__main__':
        dir_path = path.curdir
        if '-d' in argv:
                dir_path = argv[-1]
        git_path = get_git_path(dir_path)
        git_branches = get_git_branches(git_path)
        branches = []
        for branch in git_branches:
                with open(path.join(git_path, 'logs', 'refs', 'heads', branch), 'r') as branch_file:
                        lines = branch_file.readlines()
                commit_lines = [line.split()[:5] for line in lines]
                actions = []
                for i in range(len(commit_lines)):
                        line = commit_lines[i]
                        message = lines[i].split('\t')[-1].strip()
                        actions += [git_action(line[0], line[1], line[2], line[4], message)]
                branches += [git_branch(branch, actions)]
        tree = git_tree(branches)

        app = QApplication(sys.argv)
        window = tree_window(tree)
        sys.exit(app.exec_())
