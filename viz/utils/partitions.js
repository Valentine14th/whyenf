/**
 * Partition filtering utilities
 */

const GraphPartitions = (function() {
    'use strict';

    /**
     * Get all nodes that belong to the selected partitions
     * @param {Object} partitions - Object mapping partition ID to array of node IDs
     * @param {Set} selectedPartitionIds - Set of selected partition IDs
     * @returns {Set} Set of node IDs in selected partitions
     */
    function getNodesInPartitions(partitions, selectedPartitionIds) {
        const nodesInPartitions = new Set();
        
        selectedPartitionIds.forEach(partitionId => {
            if (partitions[partitionId]) {
                partitions[partitionId].forEach(nodeId => {
                    nodesInPartitions.add(nodeId);
                });
            }
        });
        
        return nodesInPartitions;
    }

    /**
     * Apply partition filter to the graph
     * @param {vis.Network} network - The vis.js network instance
     * @param {Set} selectedPartitionIds - Set of selected partition IDs
     * @param {Object} partitions - Object mapping partition ID to array of node IDs
     * @param {Function} isEdgeHidden - Function to check if edge is hidden by type filter
     * @returns {Object} Statistics about filtering
     */
    function applyPartitionFilter(network, selectedPartitionIds, partitions, isEdgeHidden) {
        if (selectedPartitionIds.size === 0) {
            // No partitions selected, show all nodes
            const allNodes = network.body.data.nodes.get();
            const nodeUpdates = allNodes.map(node => ({id: node.id, hidden: false}));
            network.body.data.nodes.update(nodeUpdates);
            
            const allEdges = network.body.data.edges.get();
            const edgeUpdates = allEdges.map(edge => ({id: edge.id, hidden: isEdgeHidden(edge)}));
            network.body.data.edges.update(edgeUpdates);
            
            return { visibleCount: allNodes.length, hiddenCount: 0 };
        }
        
        // Get nodes in selected partitions
        const visibleNodeIds = getNodesInPartitions(partitions, selectedPartitionIds);
        
        // Update node visibility - batch all updates
        const allNodes = network.body.data.nodes.get();
        let visibleCount = 0;
        let hiddenCount = 0;
        
        const nodeUpdates = allNodes.map(node => {
            const shouldShow = visibleNodeIds.has(node.id);
            if (shouldShow) visibleCount++;
            else hiddenCount++;
            return {id: node.id, hidden: !shouldShow};
        });
        network.body.data.nodes.update(nodeUpdates);
        
        // Update edge visibility - batch all updates
        const allEdges = network.body.data.edges.get();
        const edgeUpdates = allEdges.map(edge => {
            const fromVisible = visibleNodeIds.has(edge.from);
            const toVisible = visibleNodeIds.has(edge.to);
            const typeHidden = isEdgeHidden(edge);
            const hidden = !fromVisible || !toVisible || typeHidden;
            return {id: edge.id, hidden: hidden};
        });
        network.body.data.edges.update(edgeUpdates);
        
        return { visibleCount, hiddenCount };
    }

    /**
     * Apply partition filter with support for include/exclude modes
     * @param {vis.Network} network - The vis.js network instance
     * @param {Set} selectedPartitionIds - Set of selected partition IDs
     * @param {Object} partitions - Object mapping partition ID to array of node IDs
     * @param {string} filterMode - 'include' or 'exclude'
     * @param {string} edgeDirection - 'both', 'incoming', or 'outgoing'
     * @param {Function} isEdgeHidden - Function to check if edge is hidden by type filter
     * @returns {Object} Statistics about filtering
     */
    function applyPartitionFilterWithMode(network, selectedPartitionIds, partitions, filterMode, edgeDirection, isEdgeHidden) {
        if (selectedPartitionIds.size === 0) {
            // No partitions selected, show all nodes
            const allNodes = network.body.data.nodes.get();
            const nodeUpdates = allNodes.map(node => ({id: node.id, hidden: false}));
            network.body.data.nodes.update(nodeUpdates);
            
            const allEdges = network.body.data.edges.get();
            const edgeUpdates = allEdges.map(edge => ({id: edge.id, hidden: isEdgeHidden(edge)}));
            network.body.data.edges.update(edgeUpdates);
            
            return { visibleCount: allNodes.length, hiddenCount: 0, mode: filterMode };
        }
        
        // Get nodes in selected partitions
        const partitionNodeIds = getNodesInPartitions(partitions, selectedPartitionIds);
        
        if (filterMode === 'exclude') {
            // Exclude mode: hide partition nodes
            const allNodes = network.body.data.nodes.get();
            let visibleCount = 0;
            let excludedCount = 0;
            
            const nodeUpdates = allNodes.map(node => {
                const shouldHide = partitionNodeIds.has(node.id);
                if (shouldHide) excludedCount++;
                else visibleCount++;
                return {id: node.id, hidden: shouldHide};
            });
            network.body.data.nodes.update(nodeUpdates);
            
            // Update edge visibility
            const allEdges = network.body.data.edges.get();
            const edgeUpdates = allEdges.map(edge => {
                const fromVisible = !partitionNodeIds.has(edge.from);
                const toVisible = !partitionNodeIds.has(edge.to);
                const typeHidden = isEdgeHidden(edge);
                const hidden = !fromVisible || !toVisible || typeHidden;
                return {id: edge.id, hidden: hidden};
            });
            network.body.data.edges.update(edgeUpdates);
            
            return { visibleCount, excludedCount, mode: 'exclude' };
        } else {
            // Include mode: show partition nodes and their neighbors based on direction
            const allEdges = network.body.data.edges.get();
            const connectedNodeIds = new Set(partitionNodeIds);
            
            // Build neighborhood based on edge direction
            allEdges.forEach(edge => {
                if (isEdgeHidden(edge)) return;
                
                const fromInPartition = partitionNodeIds.has(edge.from);
                const toInPartition = partitionNodeIds.has(edge.to);
                
                if (edgeDirection === 'both') {
                    if (fromInPartition) connectedNodeIds.add(edge.to);
                    if (toInPartition) connectedNodeIds.add(edge.from);
                } else if (edgeDirection === 'outgoing') {
                    if (fromInPartition) connectedNodeIds.add(edge.to);
                } else if (edgeDirection === 'incoming') {
                    if (toInPartition) connectedNodeIds.add(edge.from);
                }
            });
            
            // Update node visibility
            const allNodes = network.body.data.nodes.get();
            let selectedCount = partitionNodeIds.size;
            let neighborCount = connectedNodeIds.size - partitionNodeIds.size;
            
            const nodeUpdates = allNodes.map(node => {
                const shouldShow = connectedNodeIds.has(node.id);
                return {id: node.id, hidden: !shouldShow};
            });
            network.body.data.nodes.update(nodeUpdates);
            
            // Update edge visibility
            const edgeUpdates = allEdges.map(edge => {
                const fromVisible = connectedNodeIds.has(edge.from);
                const toVisible = connectedNodeIds.has(edge.to);
                const typeHidden = isEdgeHidden(edge);
                const hidden = !fromVisible || !toVisible || typeHidden;
                return {id: edge.id, hidden: hidden};
            });
            network.body.data.edges.update(edgeUpdates);
            
            return { selectedCount, neighborCount, mode: 'include' };
        }
    }

    return {
        getNodesInPartitions,
        applyPartitionFilter,
        applyPartitionFilterWithMode
    };

})();
