/**
 * Node utilities and operations
 */

const GraphNodes = (function() {
    function getNodeName(nodeId) {
        return nodeId.startsWith('LET_') ? nodeId.substring(4) : nodeId;
    }

    function findMatchingNodeIds(network, nodeNames) {
        const allNodes = network.body.data.nodes.get();
        const matchingIds = new Set();
        
        nodeNames.forEach(nodeName => {
            const matches = allNodes.filter(node => 
                node.label === nodeName || 
                node.id === nodeName || 
                node.id === 'LET_' + nodeName
            );
            matches.forEach(m => matchingIds.add(m.id));
        });
        
        return matchingIds;
    }

    function getVisibleNodesFromEdges(network, isEdgeHiddenByTypeFilter) {
        const edges = network.body.data.edges.get();
        const connectedNodes = new Set();
        
        edges.forEach(edge => {
            if (!isEdgeHiddenByTypeFilter(edge)) {
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }
        });
        
        return connectedNodes;
    }

    function toggleNodeSelection(nodeNames, isSelected, checkboxes, selectedNodes, updateCallback, highlightCallback) {
        var nodeSet = new Set(nodeNames);
        
        checkboxes.forEach(function(cb) {
            if (nodeSet.has(cb.value)) {
                cb.checked = isSelected;
                if (isSelected) {
                    selectedNodes.add(cb.value);
                } else {
                    selectedNodes.delete(cb.value);
                }
            }
        });
        
        updateCallback();
        highlightCallback();
    }
    
    function filterDropdownByVisibility(network, connectedNodes, searchInput, checkboxItems) {
        var allNodes = network.body.data.nodes.get();
        var visibleNodeNames = new Set();
        
        // Build set of visible node names
        allNodes.forEach(function(node) {
            if (connectedNodes.has(node.id)) {
                visibleNodeNames.add(getNodeName(node.id));
            }
        });
        
        // Filter dropdown items
        var searchFilter = searchInput.value.toLowerCase();
        checkboxItems.forEach(function(item) {
            var checkbox = item.querySelector('input[type="checkbox"]');
            var label = item.querySelector('label').textContent.toLowerCase();
            var matchesSearch = label.includes(searchFilter);
            var isVisible = visibleNodeNames.has(checkbox.value);
            
            item.style.display = (matchesSearch && isVisible) ? 'flex' : 'none';
        });
    }
    
    function setupLeafSourceNodeHandlers(leafNodeNames, sourceNodeNames, checkboxes, selectedNodes, updateCallback, highlightCallback) {
        var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
        if (selectLeafNodesCheckbox && typeof leafNodeNames !== 'undefined') {
            selectLeafNodesCheckbox.addEventListener('change', function() {
                toggleNodeSelection(leafNodeNames, this.checked, checkboxes, selectedNodes, updateCallback, highlightCallback);
            });
        }
        
        var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
        if (selectSourceNodesCheckbox && typeof sourceNodeNames !== 'undefined') {
            selectSourceNodesCheckbox.addEventListener('change', function() {
                toggleNodeSelection(sourceNodeNames, this.checked, checkboxes, selectedNodes, updateCallback, highlightCallback);
            });
        }
    }

    return {
        getNodeName,
        findMatchingNodeIds,
        getVisibleNodesFromEdges,
        toggleNodeSelection,
        filterDropdownByVisibility,
        setupLeafSourceNodeHandlers
    };
})();
