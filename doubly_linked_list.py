# ############################################################################################
# This script defines a thread-safe doubly linked list (Basically a queue with O(1) deletions).
# #############################################################################################

from __future__ import annotations
import typing
import threading

# node class
class _DoublyLinkedListNode:
    __slots__ = 'data', 'prev', 'next'
    
    def __init__(self, 
                 data: typing.Any, 
                 prev_node: "_DoublyLinkedListNode | None", 
                 next_node: "_DoublyLinkedListNode | None"):
        self.data = data
        self.prev = prev_node
        self.next = next_node


class DoublyLinkedList:
    """
    Thread-safe doubly linked list (basically a dequeue).
    """

    def __init__(self):
        # using two dummy nodes (head and tail) to avoid annoying edge-case checking.
        self._head = _DoublyLinkedListNode(None, None, None)
        self._tail = _DoublyLinkedListNode(None, None, None)

        self._head.next = self._tail
        self._tail.prev = self._head

        self._size = 0
        self._lock = threading.Lock()

    def __len__(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def append(self, data: typing.Any) -> _DoublyLinkedListNode:
        # add to end
        with self._lock:
            new_node = _DoublyLinkedListNode(data, self._tail.prev, self._tail)

            if self._tail.prev:
                self._tail.prev.next = new_node

            self._tail.prev = new_node
            self._size += 1

            return new_node

    def pop_front(self) -> typing.Any:
        # remove from front
        with self._lock:
            if self.is_empty():
                raise IndexError("pop from an empty queue")
            
            node = self._head.next
            if not node or not node.next:
                raise IndexError("pop from an empty queue")

            data = node.data

            self._head.next = node.next
            node.next.prev = self._head
            self._size -= 1

            # drop references so node can be GC'd
            node.prev = node.next = node.data = None
            return data

    def peek_front(self) -> typing.Any:
        with self._lock:
            if self.is_empty() or not self._head.next:
                return None
            return self._head.next.data

    def delete_node(self, node: _DoublyLinkedListNode) -> None:
        if not isinstance(node, _DoublyLinkedListNode):
            raise TypeError("Argument must be a _DoublyLinkedListNode")
            
        with self._lock:
            # Already removed or invalid
            if node.prev is None:
                return

            if node.prev:
                node.prev.next = node.next
            if node.next:
                node.next.prev = node.prev

            self._size -= 1
            node.prev = node.next = node.data = None