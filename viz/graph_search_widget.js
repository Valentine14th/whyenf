document.addEventListener('DOMContentLoaded', function() {
    // ============================================================================
    // DOM ELEMENT REFERENCES
    // ============================================================================
    
    // Search and selection elements
    const searchInput = document.getElementById('search-input');
    const dropdownList = document.getElementById('dropdown-list');
    const selectedNodesDiv = document.getElementById('selected-nodes');
    const searchResults = document.getElementById('search-results');
    const btnClear = document.getElementById('btn-clear');
    const toggleBtn = document.getElementById('toggle-btn');
    const searchContent = document.getElementById('search-content');
    
    // Edge type filter checkboxes
    const letEdgesCheckbox = document.getElementById('show-let-edges');
    const implicationEdgesCheckbox = document.getElementById('show-implication-edges');
    const cauByCauEdgesCheckbox = document.getElementById('show-caubycau-edges');
    const cauBySupEdgesCheckbox = document.getElementById('show-caubysup-edges');
    
    // Filter controls
    const edgeDirectionRadios = document.getElementsByName('edge-direction');
    const filterModeRadios = document.getElementsByName('filter-mode');
    
    // Dropdown items
    const checkboxItems = dropdownList.querySelectorAll('.checkbox-item');
    const checkboxes = dropdownList.querySelectorAll('input[type="checkbox"]');
    
    // State
    let selectedNodes = new Set();
    
    // ============================================================================
    // EDGE TYPE UTILITIES
    // ============================================================================
    
    const EdgeColors = {
        CAU_BY_CAU: '#27ae60',
        CAU_BY_SUP: '#3498db',
        MIXED_CAUSALITY: '#9b59b6'
    };
    
    function getEdgeColor(edge) {
        return edge.color && edge.color.color ? edge.color.color : edge.color;
    }
    
    function classifyEdge(edge) {
        const edgeColor = getEdgeColor(edge);
        const isImplicationEdge = edge.dashes && edge.dashes.length > 0;
        const isCauByCauEdge = edgeColor === EdgeColors.CAU_BY_CAU;
        const isCauBySupEdge = edgeColor === EdgeColors.CAU_BY_SUP;
        const isMixedCausalityEdge = edgeColor === EdgeColors.MIXED_CAUSALITY;
        const isLetEdge = !isImplicationEdge && !isCauByCauEdge && !isCauBySupEdge && !isMixedCausalityEdge;
        
        return { isLetEdge, isImplicationEdge, isCauByCauEdge, isCauBySupEdge, isMixedCausalityEdge };
    }
    
    function getEdgeTypeVisibilitySettings() {
        return {
            showLetEdges: letEdgesCheckbox ? letEdgesCheckbox.checked : true,
            showImplicationEdges: implicationEdgesCheckbox ? implicationEdgesCheckbox.checked : true,
            showCauByCauEdges: cauByCauEdgesCheckbox ? cauByCauEdgesCheckbox.checked : true,
            showCauBySupEdges: cauBySupEdgesCheckbox ? cauBySupEdgesCheckbox.checked : true
        };
    }
    
    function isEdgeHiddenByTypeFilter(edge) {
        const settings = getEdgeTypeVisibilitySettings();
        const { isLetEdge, isImplicationEdge, isCauByCauEdge, isCauBySupEdge, isMixedCausalityEdge } = classifyEdge(edge);
        
        if (isLetEdge && !settings.showLetEdges) return true;
        if (isImplicationEdge && !settings.showImplicationEdges) return true;
        if (isCauByCauEdge && !settings.showCauByCauEdges) return true;
        if (isCauBySupEdge && !settings.showCauBySupEdges) return true;
        if (isMixedCausalityEdge && (!settings.showCauByCauEdges || !settings.showCauBySupEdges)) return true;
        
        return false;
    }
    
    // ============================================================================
    // NODE UTILITIES
    // ============================================================================
    
    function getVisibleNodesFromEdges() {
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
    
    function getNodeName(nodeId) {
        return nodeId.startsWith('LET_') ? nodeId.substring(4) : nodeId;
    }
    
    function findMatchingNodeIds(nodeNames) {
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
    
    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    // Clear all selections when network is ready
    network.once('stabilizationIterationsDone', function() {
        network.selectNodes([]);
        network.selectEdges([]);
        network.unselectAll();
    });
    
    // ============================================================================
    // DROPDOWN FILTERING
    // ============================================================================
    
    function filterDropdownByVisibility(connectedNodes) {
        const allNodes = network.body.data.nodes.get();
        const visibleNodeNames = new Set();
        
        // Build set of visible node names
        allNodes.forEach(node => {
            if (connectedNodes.has(node.id)) {
                visibleNodeNames.add(getNodeName(node.id));
            }
        });
        
        // Filter dropdown items
        const searchFilter = searchInput.value.toLowerCase();
        checkboxItems.forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const label = item.querySelector('label').textContent.toLowerCase();
            const matchesSearch = label.includes(searchFilter);
            const isVisible = visibleNodeNames.has(checkbox.value);
            
            item.style.display = (matchesSearch && isVisible) ? 'flex' : 'none';
        });
    }
    
    // ============================================================================
    // EDGE VISIBILITY MANAGEMENT
    // ============================================================================
    
    function updateEdgeVisibility() {
        const edges = network.body.data.edges.get();
        const nodes = network.body.data.nodes.get();
        const connectedNodes = new Set();
        
        // Update edges and track connected nodes
        const updatedEdges = edges.map(edge => {
            const hidden = isEdgeHiddenByTypeFilter(edge);
            
            if (!hidden) {
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }
            
            return { ...edge, hidden: hidden, physics: !hidden };
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // Update node visibility
        if (selectedNodes.size > 0) {
            highlightNodes(); // Handles node visibility with selection
        } else {
            const updatedNodes = nodes.map(node => {
                const isConnected = connectedNodes.has(node.id);
                return { ...node, hidden: !isConnected };
            });
            network.body.data.nodes.update(updatedNodes);
        }
        
        filterDropdownByVisibility(connectedNodes);
    }
    
    // ============================================================================
    // NODE HIGHLIGHTING (MAIN FILTER LOGIC)
    // ============================================================================
    
    function getSelectedEdgeDirection() {
        let direction = 'both';
        edgeDirectionRadios.forEach(radio => {
            if (radio.checked) direction = radio.value;
        });
        return direction;
    }
    
    function getSelectedFilterMode() {
        let mode = 'include';
        filterModeRadios.forEach(radio => {
            if (radio.checked) mode = radio.value;
        });
        return mode;
    }
    
    function shouldIncludeEdge(edge, matchingIds, edgeDirection) {
        if (isEdgeHiddenByTypeFilter(edge)) return false;
        
        const isOutgoing = matchingIds.has(edge.from);
        const isIncoming = matchingIds.has(edge.to);
        
        if (edgeDirection === 'both') return isOutgoing || isIncoming;
        if (edgeDirection === 'outgoing') return isOutgoing;
        if (edgeDirection === 'incoming') return isIncoming;
        
        return false;
    }
    
    function buildNeighborhoodFromEdges(matchingIds, edgeDirection) {
        const allEdges = network.body.data.edges.get();
        const connectedNodeIds = new Set(matchingIds);
        
        allEdges.forEach(edge => {
            if (!shouldIncludeEdge(edge, matchingIds, edgeDirection)) return;
            
            const isOutgoing = matchingIds.has(edge.from);
            const isIncoming = matchingIds.has(edge.to);
            
            if (isOutgoing) connectedNodeIds.add(edge.to);
            if (isIncoming) connectedNodeIds.add(edge.from);
        });
        
        return connectedNodeIds;
    }
    
    function applyExcludeMode(matchingIds) {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        
        // Hide edges connected to excluded nodes
        const updatedEdges = allEdges.map(edge => {
            const hiddenByTypeFilter = isEdgeHiddenByTypeFilter(edge);
            const connectedToExcluded = matchingIds.has(edge.from) || matchingIds.has(edge.to);
            const hidden = hiddenByTypeFilter || connectedToExcluded;
            return { ...edge, hidden: hidden, physics: !hidden };
        });
        
        // Collect nodes with visible edges
        const nodesWithVisibleEdges = new Set();
        updatedEdges.forEach(edge => {
            if (!edge.hidden) {
                nodesWithVisibleEdges.add(edge.from);
                nodesWithVisibleEdges.add(edge.to);
            }
        });
        
        // Hide excluded nodes and nodes with no visible edges
        const updatedNodes = allNodes.map(node => {
            const isExcluded = matchingIds.has(node.id);
            const hasNoEdges = !nodesWithVisibleEdges.has(node.id);
            return { ...node, hidden: isExcluded || hasNoEdges };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.body.data.edges.update(updatedEdges);
        network.selectNodes([]);
        
        const visibleCount = allNodes.filter(node => 
            !matchingIds.has(node.id) && nodesWithVisibleEdges.has(node.id)
        ).length;
        
        searchResults.textContent = `Excluded ${matchingIds.size} node${matchingIds.size > 1 ? 's' : ''} (showing ${visibleCount})`;
        searchResults.style.color = '#2c3e50';
    }
    
    function applyIncludeMode(matchingIds, connectedNodeIds) {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        const edgeDirection = getSelectedEdgeDirection();
        
        // Update edge visibility
        const updatedEdges = allEdges.map(edge => {
            if (isEdgeHiddenByTypeFilter(edge)) {
                return { ...edge, hidden: true, physics: false };
            }
            
            if (!shouldIncludeEdge(edge, matchingIds, edgeDirection)) {
                return { ...edge, hidden: true, physics: false };
            }
            
            const isOutgoing = matchingIds.has(edge.from);
            const isIncoming = matchingIds.has(edge.to);
            const edgeVisible = isOutgoing || isIncoming;
            
            return { ...edge, hidden: !edgeVisible, physics: edgeVisible };
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // Update node visibility
        const updatedNodes = allNodes.map(node => {
            return { ...node, hidden: !connectedNodeIds.has(node.id) };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.selectNodes(Array.from(matchingIds));
        
        searchResults.textContent = `Showing ${matchingIds.size} selected node${matchingIds.size > 1 ? 's' : ''} with ${connectedNodeIds.size - matchingIds.size} neighbor${connectedNodeIds.size - matchingIds.size !== 1 ? 's' : ''}`;
        searchResults.style.color = '#27ae60';
    }
    
    function highlightNodes() {
        if (selectedNodes.size === 0) {
            network.selectNodes([]);
            searchResults.textContent = '';
            updateEdgeVisibility();
            return;
        }
        
        const matchingIds = findMatchingNodeIds(selectedNodes);
        
        if (matchingIds.size === 0) {
            searchResults.textContent = 'No matching nodes found';
            searchResults.style.color = '#e74c3c';
            return;
        }
        
        const filterMode = getSelectedFilterMode();
        
        if (filterMode === 'exclude') {
            applyExcludeMode(matchingIds);
        } else {
            const edgeDirection = getSelectedEdgeDirection();
            const connectedNodeIds = buildNeighborhoodFromEdges(matchingIds, edgeDirection);
            applyIncludeMode(matchingIds, connectedNodeIds);
        }
    }
    
    // ============================================================================
    // SELECTED NODES DISPLAY
    // ============================================================================
    
    function updateSelectedDisplay() {
        selectedNodesDiv.innerHTML = '';
        
        if (selectedNodes.size === 0) {
            selectedNodesDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No nodes selected</div>';
            return;
        }
        
        selectedNodes.forEach(nodeName => {
            const tag = document.createElement('span');
            tag.className = 'selected-tag';
            tag.textContent = nodeName;
            tag.onclick = () => {
                selectedNodes.delete(nodeName);
                checkboxes.forEach(cb => {
                    if (cb.value === nodeName) cb.checked = false;
                });
                updateSelectedDisplay();
                highlightNodes();
            };
            selectedNodesDiv.appendChild(tag);
        });
    }
    
    // ============================================================================
    // EVENT HANDLERS - EDGE TYPE TOGGLES
    // ============================================================================
    
    if (letEdgesCheckbox) letEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    if (implicationEdgesCheckbox) implicationEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    if (cauByCauEdgesCheckbox) cauByCauEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    if (cauBySupEdgesCheckbox) cauBySupEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    
    edgeDirectionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (selectedNodes.size > 0) highlightNodes();
        });
    });
    
    function updateEdgeDirectionAvailability() {
        const filterMode = getSelectedFilterMode();
        const isExcludeMode = filterMode === 'exclude';
        
        edgeDirectionRadios.forEach(radio => {
            radio.disabled = isExcludeMode;
            if (radio.parentElement) {
                radio.parentElement.style.opacity = isExcludeMode ? '0.5' : '1';
                radio.parentElement.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        });
    }
    
    filterModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateEdgeDirectionAvailability();
            if (selectedNodes.size > 0) highlightNodes();
        });
    });
    
    // ============================================================================
    // EVENT HANDLERS - SEARCH AND SELECTION
    // ============================================================================
    
    toggleBtn.addEventListener('click', function() {
        if (searchContent.classList.contains('hidden')) {
            searchContent.classList.remove('hidden');
            toggleBtn.textContent = 'Hide';
        } else {
            searchContent.classList.add('hidden');
            toggleBtn.textContent = 'Show';
        }
    });
    
    searchInput.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        const connectedNodes = getVisibleNodesFromEdges();
        
        const allNodes = network.body.data.nodes.get();
        const visibleNodeNames = new Set();
        allNodes.forEach(node => {
            if (connectedNodes.has(node.id)) {
                visibleNodeNames.add(getNodeName(node.id));
            }
        });
        
        checkboxItems.forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const label = item.querySelector('label').textContent.toLowerCase();
            const isVisible = visibleNodeNames.has(checkbox.value);
            item.style.display = (label.includes(filter) && isVisible) ? 'flex' : 'none';
        });
    });
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                selectedNodes.add(this.value);
            } else {
                selectedNodes.delete(this.value);
            }
            updateSelectedDisplay();
            highlightNodes();
        });
    });
    
    // Make clicking on label/item also toggle checkbox
    checkboxItems.forEach(item => {
        item.addEventListener('click', function(e) {
            if (e.target.tagName !== 'INPUT') {
                const checkbox = this.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    });
    
    btnClear.addEventListener('click', function() {
        selectedNodes.clear();
        checkboxes.forEach(cb => cb.checked = false);
        
        // Uncheck special selection checkboxes
        const selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
        const selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
        if (selectLeafNodesCheckbox) selectLeafNodesCheckbox.checked = false;
        if (selectSourceNodesCheckbox) selectSourceNodesCheckbox.checked = false;
        
        updateSelectedDisplay();
        network.selectNodes([]);
        searchResults.textContent = '';
        searchInput.value = '';
        checkboxItems.forEach(item => item.style.display = 'flex');
        
        updateEdgeVisibility();
    });
    
    // ============================================================================
    // EVENT HANDLERS - SPECIAL NODE SELECTIONS
    // ============================================================================
    
    function toggleNodeSelection(nodeNames, isSelected) {
        const nodeSet = new Set(nodeNames);
        
        checkboxes.forEach(cb => {
            if (nodeSet.has(cb.value)) {
                cb.checked = isSelected;
                if (isSelected) {
                    selectedNodes.add(cb.value);
                } else {
                    selectedNodes.delete(cb.value);
                }
            }
        });
        
        updateSelectedDisplay();
        highlightNodes();
    }
    
    const selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
    if (selectLeafNodesCheckbox && typeof leafNodeNames !== 'undefined') {
        selectLeafNodesCheckbox.addEventListener('change', function() {
            toggleNodeSelection(leafNodeNames, this.checked);
        });
    }
    
    const selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
    if (selectSourceNodesCheckbox && typeof sourceNodeNames !== 'undefined') {
        selectSourceNodesCheckbox.addEventListener('change', function() {
            toggleNodeSelection(sourceNodeNames, this.checked);
        });
    }
    
    // ============================================================================
    // RANKINGS WIDGET
    // ============================================================================
    
    function updateRankings() {
        const outgoingRanking = document.getElementById('outgoing-ranking');
        const inboundRanking = document.getElementById('inbound-ranking');
        
        if (!outgoingRanking || !inboundRanking) return;
        
        const visibleNodes = network.body.data.nodes.get().filter(node => !node.hidden);
        const visibleEdges = network.body.data.edges.get().filter(edge => !edge.hidden && !isEdgeHiddenByTypeFilter(edge));
        
        // Count edges for each node
        const outgoingCounts = {};
        const inboundCounts = {};
        
        visibleNodes.forEach(node => {
            outgoingCounts[node.id] = 0;
            inboundCounts[node.id] = 0;
        });
        
        visibleEdges.forEach(edge => {
            if (outgoingCounts.hasOwnProperty(edge.from)) outgoingCounts[edge.from]++;
            if (inboundCounts.hasOwnProperty(edge.to)) inboundCounts[edge.to]++;
        });
        
        // Sort and slice top 15
        const sortedByOutgoing = visibleNodes
            .map(node => ({ id: node.id, label: node.label, count: outgoingCounts[node.id] }))
            .filter(item => item.count > 0)
            .sort((a, b) => b.count - a.count)
            .slice(0, 15);
        
        const sortedByInbound = visibleNodes
            .map(node => ({ id: node.id, label: node.label, count: inboundCounts[node.id] }))
            .filter(item => item.count > 0)
            .sort((a, b) => b.count - a.count)
            .slice(0, 15);
        
        // Render rankings
        renderRanking(outgoingRanking, sortedByOutgoing);
        renderRanking(inboundRanking, sortedByInbound);
    }
    
    function renderRanking(container, items) {
        container.innerHTML = '';
        
        if (items.length === 0) {
            container.innerHTML = '<div style="color: #95a5a6; font-size: 11px; padding: 5px;">No edges</div>';
            return;
        }
        
        items.forEach((item, index) => {
            const rankItem = document.createElement('div');
            rankItem.className = 'ranking-item';
            
            const nodeName = getNodeName(item.id);
            if (selectedNodes.has(item.label) || selectedNodes.has(nodeName)) {
                rankItem.classList.add('selected');
            }
            
            rankItem.innerHTML = `
                <span class="node-name" title="${item.label}">${index + 1}. ${item.label}</span>
                <span class="edge-count">${item.count}</span>
            `;
            
            rankItem.addEventListener('click', function() {
                const checkbox = Array.from(checkboxes).find(cb => cb.value === nodeName);
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
            
            container.appendChild(rankItem);
        });
    }
    
    const rankingsToggleBtn = document.getElementById('rankings-toggle-btn');
    const rankingsContent = document.getElementById('rankings-content');
    const rankingsHeader = document.getElementById('rankings-header');
    
    if (rankingsToggleBtn && rankingsContent && rankingsHeader) {
        rankingsToggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (rankingsContent.classList.contains('collapsed')) {
                rankingsContent.classList.remove('collapsed');
                rankingsToggleBtn.textContent = 'Hide';
            } else {
                rankingsContent.classList.add('collapsed');
                rankingsToggleBtn.textContent = 'Show';
            }
        });
        
        rankingsHeader.addEventListener('click', function(e) {
            if (e.target !== rankingsToggleBtn) {
                rankingsToggleBtn.click();
            }
        });
    }
    
    // Hook rankings update into highlight and edge visibility functions
    const originalHighlightNodes = highlightNodes;
    highlightNodes = function() {
        originalHighlightNodes();
        updateRankings();
    };
    
    const originalUpdateEdgeVisibility = updateEdgeVisibility;
    updateEdgeVisibility = function() {
        originalUpdateEdgeVisibility();
        updateRankings();
    };
    
    // ============================================================================
    // INITIALIZATION - DEFAULT STATE
    // ============================================================================
    
    // Clear selections
    selectedNodes.clear();
    checkboxes.forEach(cb => cb.checked = false);
    searchInput.value = '';
    searchResults.textContent = '';
    
    // Set default edge type visibility
    if (letEdgesCheckbox) letEdgesCheckbox.checked = true;
    if (implicationEdgesCheckbox) implicationEdgesCheckbox.checked = true;
    if (cauByCauEdgesCheckbox) cauByCauEdgesCheckbox.checked = true;
    if (cauBySupEdgesCheckbox) cauBySupEdgesCheckbox.checked = true;
    
    // Set default edge direction
    edgeDirectionRadios.forEach(radio => {
        if (radio.value === 'both') radio.checked = true;
    });
    
    // Initialize edge direction availability based on filter mode
    updateEdgeDirectionAvailability();
    
    // Initialize display and rankings
    updateSelectedDisplay();
    updateRankings();
});
