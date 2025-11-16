# #####################################################################
# ## PART 2: DOUBLY-LINKED LIST IMPLEMENTATION (Corrected)
# ## File: doubly_linked_list.py
# #####################################################################

from __future__ import annotations
import threading
import typing

# ---
# ## FIX 1: The Node class is moved outside.
# ---
# We name it with a single underscore to mark it as "internal"
# to this module, which is standard Python practice.
# ---

class _DoublyLinkedListNode:
    """Internal node class for DoublyLinkedList."""
    __slots__ = 'data', 'prev', 'next'
    
    def __init__(self, 
                 data: typing.Any, 
                 prev_node: "_DoublyLinkedListNode | None", 
                 next_node: "_DoublyLinkedListNode | None"):
        self.data: typing.Any = data
        self.prev: "_DoublyLinkedListNode | None" = prev_node
        self.next: "_DoublyLinkedListNode | None" = next_node

# ---
# ## FIX 2: The LinkedList class is now clean and simple.
# ---

class DoublyLinkedList:
    """
    A thread-safe implementation of a Doubly-Linked List (Deque)
    that supports O(1) random deletion of nodes.
    
    This is a core component of the specified HYBRIDJOIN algorithm.
    """

    def __init__(self):
        """Initializes an empty list with head/tail sentinel nodes."""
        
        # All type hints are now simple and clear.
        self._head: _DoublyLinkedListNode = _DoublyLinkedListNode(None, None, None)
        self._tail: _DoublyLinkedListNode = _DoublyLinkedListNode(None, None, None)
        
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size: int = 0
        self._lock: threading.Lock = threading.Lock()

    def __len__(self) -> int:
        """Returns the number of elements in the list."""
        return self._size

    def is_empty(self) -> bool:
        """Returns True if the list is empty, False otherwise."""
        return self._size == 0

    def append(self, data: typing.Any) -> _DoublyLinkedListNode:
        """Adds data to the end (tail) of the list.
        
        Returns:
            The newly created _DoublyLinkedListNode object for O(1) deletion.
        """
        with self._lock:
            # The type hint "_DoublyLinkedListNode" is now valid
            new_node = _DoublyLinkedListNode(data, self._tail.prev, self._tail)
            if self._tail.prev:
                self._tail.prev.next = new_node
            self._tail.prev = new_node
            self._size += 1
            return new_node

    def pop_front(self) -> typing.Any:
        """Removes and returns data from the front (head).
        
        Raises:
            IndexError: If the queue is empty.
        """
        with self._lock:
            if self.is_empty():
                raise IndexError("pop from an empty queue")
            
            node_to_remove = self._head.next
            if not node_to_remove or not node_to_remove.next:
                raise IndexError("pop from an empty queue")

            data = node_to_remove.data
            self._head.next = node_to_remove.next
            node_to_remove.next.prev = self._head
            self._size -= 1
            
            node_to_remove.prev = node_to_remove.next = node_to_remove.data = None
            return data

    def peek_front(self) -> typing.Any:
        """Returns the data at the front (head) without removing."""
        with self._lock:
            if self.is_empty() or not self._head.next:
                return None
            return self._head.next.data

    def delete_node(self, node: _DoublyLinkedListNode) -> None:
        """Removes a specific node from the list in O(1) time."""
        
        # The type check is now simple
        if not isinstance(node, _DoublyLinkedListNode):
            raise TypeError("Argument must be a _DoublyLinkedListNode")
            
        with self._lock:
            if node.prev is None:
                return  # Already deleted
            
            # This logic is now safer and linter-friendly
            if node.prev:
                node.prev.next = node.next
            if node.next:
                node.next.prev = node.prev
            
            self._size -= 1
            node.prev = node.next = node.data = None