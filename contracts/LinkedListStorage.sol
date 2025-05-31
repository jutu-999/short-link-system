// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LinkedListStorage {
    // 定义节点结构
    struct Node {
        uint256 data;       // 存储的数据
        bytes32 nextNodeHash; // 下一个节点的哈希值，作为链表的链接
        bytes32 prevNodeHash; // 上一个节点的哈希值，可选，用于双向链表
    }

    // 存储所有节点的映射：哈希值 => 节点
    mapping(bytes32 => Node) public nodes;
    // 存储链表头部的哈希值
    bytes32 public headNodeHash;
    // 存储链表尾部的哈希值
    bytes32 public tailNodeHash;

    // 事件：当新节点添加时触发
    event NodeAdded(bytes32 indexed nodeHash, uint256 data, bytes32 prevHash, bytes32 nextHash);
    // 事件：当节点数据更新时触发
    event NodeUpdated(bytes32 indexed nodeHash, uint256 oldData, uint256 newData);
    // 事件：当节点删除时触发
    event NodeDeleted(bytes32 indexed nodeHash, uint256 data);

    constructor() {
        // 构造函数，初始化链表为空
        headNodeHash = bytes32(0); // 0x0...0 表示空哈希
        tailNodeHash = bytes32(0);
    }

    /**
     * @dev 添加一个新节点到链表尾部
     * @param _data 要存储的数据
     * @return 新节点的哈希值
     */
    function addNode(uint256 _data) public returns (bytes32) {
        bytes32 newNodeHash = keccak256(abi.encodePacked(_data, block.timestamp, msg.sender)); // 使用keccak256生成唯一哈希

        require(nodes[newNodeHash].data == 0, "Node with this hash already exists."); // 简单检查哈希冲突，实际应用中需要更严谨

        Node storage newNode = nodes[newNodeHash];
        newNode.data = _data;
        newNode.nextNodeHash = bytes32(0); // 新节点当前是尾部，没有下一个节点

        if (headNodeHash == bytes32(0)) { // 如果链表为空
            headNodeHash = newNodeHash;
            tailNodeHash = newNodeHash;
            newNode.prevNodeHash = bytes32(0);
        } else {
            // 更新当前尾部的下一个节点指向新节点
            nodes[tailNodeHash].nextNodeHash = newNodeHash;
            newNode.prevNodeHash = tailNodeHash; // 新节点的上一个节点是旧尾部
            tailNodeHash = newNodeHash; // 更新尾部为新节点
        }

        emit NodeAdded(newNodeHash, _data, newNode.prevNodeHash, newNode.nextNodeHash);
        return newNodeHash;
    }

    /**
     * @dev 根据哈希获取节点数据
     * @param _nodeHash 节点的哈希值
     * @return 节点的数据
     */
    function getNodeData(bytes32 _nodeHash) public view returns (uint256) {
        require(nodes[_nodeHash].data != 0 || _nodeHash == headNodeHash || _nodeHash == tailNodeHash, "Node does not exist.");
        return nodes[_nodeHash].data;
    }

    /**
     * @dev 更新节点数据
     * @param _nodeHash 要更新的节点哈希
     * @param _newData 新的数据
     */
    function updateNodeData(bytes32 _nodeHash, uint256 _newData) public {
        require(nodes[_nodeHash].data != 0, "Node does not exist for update.");
        uint256 oldData = nodes[_nodeHash].data;
        nodes[_nodeHash].data = _newData;
        emit NodeUpdated(_nodeHash, oldData, _newData);
    }

    /**
     * @dev 获取链表头部的哈希值
     * @return 头部哈希值
     */
    function getHeadNodeHash() public view returns (bytes32) {
        return headNodeHash;
    }

    /**
     * @dev 获取链表尾部的哈希值
     * @return 尾部哈希值
     */
    function getTailNodeHash() public view returns (bytes32) {
        return tailNodeHash;
    }

    // 可以在此添加删除节点、遍历链表等更复杂的功能
}