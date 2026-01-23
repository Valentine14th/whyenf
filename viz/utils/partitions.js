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
     * Get nodes that are common to ALL selected partitions (intersection)
     * @param {Object} partitions - Object mapping partition ID to array of node IDs
     * @param {Set} selectedPartitionIds - Set of selected partition IDs
     * @returns {Set} Set of node IDs present in all selected partitions
     */
    function getCommonNodes(partitions, selectedPartitionIds) {
        if (selectedPartitionIds.size === 0) {
            return new Set();
        }
        
        const partitionArrays = Array.from(selectedPartitionIds).map(id => 
            partitions[id] ? new Set(partitions[id]) : new Set()
        );
        
        if (partitionArrays.length === 0) {
            return new Set();
        }
        
        // Start with the first partition
        const commonNodes = new Set(partitionArrays[0]);
        
        // Intersect with all other partitions
        for (let i = 1; i < partitionArrays.length; i++) {
            const currentPartition = partitionArrays[i];
            // Remove nodes not in current partition
            for (const node of commonNodes) {
                if (!currentPartition.has(node)) {
                    commonNodes.delete(node);
                }
            }
        }
        
        return commonNodes;
    }

    /**
     * Reset node highlighting (remove golden border and thick width)
     * @param {Object} node - Node object from vis.js
     * @param {Object} update - Update object to modify
     */
    function resetNodeHighlight(node, update) {
        if (node.borderWidth === 5) {
            update.borderWidth = 2;
        }
        if (node.color && node.color.border === '#FFD700') {
            update.color = {border: node.originalBorder || '#2B7CE9'};
        }
    }

    /**
     * Apply highlight to a common node (golden border and thick width)
     * @param {Object} node - Node object from vis.js
     * @param {Object} update - Update object to modify
     * @param {vis.Network} network - The vis.js network instance
     */
    function highlightCommonNode(node, update, network) {
        // Store original border color if not already stored
        if (!node.originalBorder && node.color && node.color.border) {
            const originalNode = network.body.data.nodes.get(node.id);
            network.body.data.nodes.update({
                id: node.id, 
                originalBorder: originalNode.color.border
            });
        }
        update.borderWidth = 5;
        update.color = {border: '#FFD700'}; // Gold color for common nodes
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
            // No partitions selected, show all nodes with default styling
            const allNodes = network.body.data.nodes.get();
            const nodeUpdates = allNodes.map(node => {
                const update = {id: node.id, hidden: false};
                resetNodeHighlight(node, update);
                return update;
            });
            network.body.data.nodes.update(nodeUpdates);
            
            const allEdges = network.body.data.edges.get();
            const edgeUpdates = allEdges.map(edge => ({id: edge.id, hidden: isEdgeHidden(edge)}));
            network.body.data.edges.update(edgeUpdates);
            
            return { visibleCount: allNodes.length, hiddenCount: 0, mode: filterMode };
        }
        
        // Get nodes in selected partitions
        const partitionNodeIds = getNodesInPartitions(partitions, selectedPartitionIds);
        
        // Get common nodes if multiple partitions selected
        const commonNodeIds = selectedPartitionIds.size > 1 
            ? getCommonNodes(partitions, selectedPartitionIds) 
            : new Set();
        
        if (filterMode === 'exclude') {
            // Exclude mode: hide partition nodes
            const allNodes = network.body.data.nodes.get();
            let visibleCount = 0;
            let excludedCount = 0;
            
            const nodeUpdates = allNodes.map(node => {
                const shouldHide = partitionNodeIds.has(node.id);
                if (shouldHide) excludedCount++;
                else visibleCount++;
                
                const update = {id: node.id, hidden: shouldHide};
                
                // Reset highlight for excluded nodes or non-common visible nodes
                if (shouldHide || !commonNodeIds.has(node.id)) {
                    resetNodeHighlight(node, update);
                }
                
                return update;
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
            
            return { visibleCount, excludedCount, commonCount: commonNodeIds.size, mode: 'exclude' };
        } else {
            // Include mode: show only partition nodes and edges between them
            const allNodes = network.body.data.nodes.get();
            let selectedCount = partitionNodeIds.size;
            
            const nodeUpdates = allNodes.map(node => {
                const shouldShow = partitionNodeIds.has(node.id);
                const isCommon = commonNodeIds.has(node.id);
                
                const update = {id: node.id, hidden: !shouldShow};
                
                // Highlight common nodes with golden border and increased width
                if (shouldShow && isCommon) {
                    highlightCommonNode(node, update, network);
                } else if (shouldShow) {
                    // Reset highlighting for non-common nodes
                    resetNodeHighlight(node, update);
                }
                
                return update;
            });
            network.body.data.nodes.update(nodeUpdates);
            
            // Update edge visibility - only show edges between partition nodes
            const allEdges = network.body.data.edges.get();
            const edgeUpdates = allEdges.map(edge => {
                const fromInPartition = partitionNodeIds.has(edge.from);
                const toInPartition = partitionNodeIds.has(edge.to);
                const typeHidden = isEdgeHidden(edge);
                // Only show edge if both endpoints are in the partition
                const hidden = !fromInPartition || !toInPartition || typeHidden;
                return {id: edge.id, hidden: hidden};
            });
            network.body.data.edges.update(edgeUpdates);
            
            return { selectedCount, neighborCount: 0, commonCount: commonNodeIds.size, mode: 'include' };
        }
    }

    /**
     * Initialize partition statistics display
     */
    function initializePartitionStats() {
        // Display partition stats on load
        function updateStatsDisplay(stats) {
            var statsDiv = document.getElementById('partition-stats');
            if (statsDiv && stats) {
                statsDiv.innerHTML = 
                    '<div style="margin-bottom: 2px;"><strong>Initial partitions:</strong> ' + stats.initial_count + '</div>' +
                    '<div style="margin-bottom: 2px;"><strong>After merging:</strong> ' + stats.merged_count + '</div>' +
                    '<div style="font-style: italic;">Strategy: ' + stats.strategy + '</div>';
            }
        }
        
        // Set initial stats
        if (window.graphData && window.graphData.stats) {
            updateStatsDisplay(window.graphData.stats);
        }
    }

    function setupPartitionSearchHandler(partitionSearchInput, partitionItems) {
        if (partitionSearchInput) {
            partitionSearchInput.addEventListener('input', function() {
                var filter = this.value.toLowerCase();
                partitionItems.forEach(function(item) {
                    var label = item.querySelector('label').textContent.toLowerCase();
                    item.style.display = label.includes(filter) ? 'flex' : 'none';
                });
            });
        }
    }
    
    function setupPartitionCheckboxHandlers(partitionCheckboxes, selectedPartitions, updateCallback, highlightCallback) {
        partitionCheckboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedPartitions.add(this.value);
                } else {
                    selectedPartitions.delete(this.value);
                }
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupPartitionItemClickHandlers(partitionItems) {
        partitionItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
                    var checkbox = this.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }

    return {
        getNodesInPartitions,
        getCommonNodes,
        applyPartitionFilter,
        applyPartitionFilterWithMode,
        initializePartitionStats,
        setupPartitionSearchHandler,
        setupPartitionCheckboxHandlers,
        setupPartitionItemClickHandlers
    };

})();
