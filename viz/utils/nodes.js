/**
 * Node utilities and operations
 */

const GraphNodes = (function() {
    /**
     * Extract the display name from a node ID.
     * Formats: RULE_1 -> "Rule 1", LET_foo -> "foo", others -> unchanged
     */
    function getNodeDisplayName(nodeId) {
        if (nodeId.startsWith('RULE_')) {
            return 'Rule ' + nodeId.substring(5);
        }
        return nodeId;
    }

    function findMatchingNodeIds(network, nodeNames) {
        const allNodes = network.body.data.nodes.get();
        const matchingIds = new Set();
        
        nodeNames.forEach(nodeName => {
            const matches = allNodes.filter(node => 
                node.label === nodeName || 
                node.id === nodeName
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

    function setupSearchHandlers(searchInput, checkboxItems, network, isEdgeHidden) {
        searchInput.addEventListener('input', function() {
            var filter = this.value.toLowerCase();
            
            checkboxItems.forEach(function(item) {
                var label = item.querySelector('label').textContent.toLowerCase();
                item.style.display = label.includes(filter) ? 'flex' : 'none';
            });
        });
    }
    
    function setupNodeCheckboxHandlers(checkboxes, selectedNodes, updateCallback, highlightCallback) {
        checkboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedNodes.add(this.value);
                } else {
                    selectedNodes.delete(this.value);
                }
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupSCCCheckboxHandlers(sccCheckboxes, nodeCheckboxes, selectedNodes, updateCallback, highlightCallback) {
        sccCheckboxes.forEach(function(sccCheckbox) {
            sccCheckbox.addEventListener('change', function() {
                // Get the SCC nodes from data attribute
                const sccNodes = JSON.parse(this.getAttribute('data-scc-nodes'));
                
                if (this.checked) {
                    // Select all nodes in the SCC
                    sccNodes.forEach(nodeId => {
                        selectedNodes.add(nodeId);
                        // Also check the individual node checkbox if it exists
                        const nodeCheckbox = Array.from(nodeCheckboxes).find(cb => cb.value === nodeId);
                        if (nodeCheckbox) {
                            nodeCheckbox.checked = true;
                        }
                    });
                } else {
                    // Deselect all nodes in the SCC
                    sccNodes.forEach(nodeId => {
                        selectedNodes.delete(nodeId);
                        // Also uncheck the individual node checkbox if it exists
                        const nodeCheckbox = Array.from(nodeCheckboxes).find(cb => cb.value === nodeId);
                        if (nodeCheckbox) {
                            nodeCheckbox.checked = false;
                        }
                    });
                }
                
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupItemClickHandlers(checkboxItems) {
        checkboxItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName !== 'INPUT') {
                    var checkbox = this.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }

    return {
        getNodeDisplayName,
        findMatchingNodeIds,
        getVisibleNodesFromEdges,
        toggleNodeSelection,
        setupLeafSourceNodeHandlers,
        setupSearchHandlers,
        setupNodeCheckboxHandlers,
        setupSCCCheckboxHandlers,
        setupItemClickHandlers
    };
})();
