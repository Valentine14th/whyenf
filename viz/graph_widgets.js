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
    const edgeCheckboxes = {
        letEdges: document.getElementById('show-let-edges'),
        implicationEdges: document.getElementById('show-implication-edges'),
        cauByCauEdges: document.getElementById('show-caubycau-edges'),
        cauBySupEdges: document.getElementById('show-caubysup-edges')
    };
    
    // Filter controls
    const edgeDirectionRadios = document.getElementsByName('edge-direction');
    const filterModeRadios = document.getElementsByName('filter-mode');
    
    // Dropdown items
    const checkboxItems = dropdownList.querySelectorAll('.checkbox-item');
    const checkboxes = dropdownList.querySelectorAll('input[type="checkbox"]');
    
    // State
    let selectedNodes = new Set();
    
    // ============================================================================
    // HELPER FUNCTIONS WITH CLOSURES
    // ============================================================================
    
    const isEdgeHidden = (edge) => GraphEdges.isEdgeHiddenByTypeFilter(edge, edgeCheckboxes);
    
    function filterDropdownByVisibility(connectedNodes) {
        const allNodes = network.body.data.nodes.get();
        const visibleNodeNames = new Set();
        
        // Build set of visible node names
        allNodes.forEach(node => {
            if (connectedNodes.has(node.id)) {
                visibleNodeNames.add(GraphNodes.getNodeName(node.id));
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
    
    function handleEdgeVisibilityUpdate() {
        const connectedNodes = GraphFilters.updateEdgeVisibility(network, selectedNodes, isEdgeHidden, highlightNodes);
        filterDropdownByVisibility(connectedNodes);
        GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
    }
    
    function highlightNodes() {
        if (selectedNodes.size === 0) {
            network.selectNodes([]);
            searchResults.textContent = '';
            handleEdgeVisibilityUpdate();
            return;
        }
        
        const matchingIds = GraphNodes.findMatchingNodeIds(network, selectedNodes);
        
        if (matchingIds.size === 0) {
            searchResults.textContent = 'No matching nodes found';
            searchResults.style.color = '#e74c3c';
            return;
        }
        
        const filterMode = GraphFilters.getSelectedFilterMode(filterModeRadios);
        
        if (filterMode === 'exclude') {
            const result = GraphFilters.applyExcludeMode(network, matchingIds, isEdgeHidden);
            searchResults.textContent = `Excluded ${result.excludedCount} node${result.excludedCount > 1 ? 's' : ''} (showing ${result.visibleCount})`;
            searchResults.style.color = '#2c3e50';
        } else {
            const edgeDirection = GraphFilters.getSelectedEdgeDirection(edgeDirectionRadios);
            const connectedNodeIds = GraphFilters.buildNeighborhoodFromEdges(network, matchingIds, edgeDirection, isEdgeHidden);
            const result = GraphFilters.applyIncludeMode(network, matchingIds, connectedNodeIds, edgeDirection, isEdgeHidden);
            searchResults.textContent = `Showing ${result.selectedCount} selected node${result.selectedCount > 1 ? 's' : ''} with ${result.neighborCount} neighbor${result.neighborCount !== 1 ? 's' : ''}`;
            searchResults.style.color = '#27ae60';
        }
        
        GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
    }
    
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
    
    function updateFilterModeControls() {
        const filterMode = GraphFilters.getSelectedFilterMode(filterModeRadios);
        const isExcludeMode = filterMode === 'exclude';
        
        edgeDirectionRadios.forEach(radio => {
            radio.disabled = isExcludeMode;
            if (radio.parentElement) {
                radio.parentElement.style.opacity = isExcludeMode ? '0.5' : '1';
                radio.parentElement.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        });
        
        // Also disable leaf/source node selection checkboxes in exclude mode
        const selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
        const selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
        
        if (selectLeafNodesCheckbox) {
            selectLeafNodesCheckbox.disabled = isExcludeMode;
            const leafLabel = selectLeafNodesCheckbox.parentElement;
            if (leafLabel) {
                leafLabel.style.opacity = isExcludeMode ? '0.5' : '1';
                leafLabel.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        }
        
        if (selectSourceNodesCheckbox) {
            selectSourceNodesCheckbox.disabled = isExcludeMode;
            const sourceLabel = selectSourceNodesCheckbox.parentElement;
            if (sourceLabel) {
                sourceLabel.style.opacity = isExcludeMode ? '0.5' : '1';
                sourceLabel.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        }
    }
    
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
    // EVENT HANDLERS - EDGE TYPE TOGGLES
    // ============================================================================
    
    if (edgeCheckboxes.letEdges) edgeCheckboxes.letEdges.addEventListener('change', handleEdgeVisibilityUpdate);
    if (edgeCheckboxes.implicationEdges) edgeCheckboxes.implicationEdges.addEventListener('change', handleEdgeVisibilityUpdate);
    if (edgeCheckboxes.cauByCauEdges) edgeCheckboxes.cauByCauEdges.addEventListener('change', handleEdgeVisibilityUpdate);
    if (edgeCheckboxes.cauBySupEdges) edgeCheckboxes.cauBySupEdges.addEventListener('change', handleEdgeVisibilityUpdate);
    
    edgeDirectionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (selectedNodes.size > 0) highlightNodes();
        });
    });
    
    filterModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateFilterModeControls();
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
        const connectedNodes = GraphNodes.getVisibleNodesFromEdges(network, isEdgeHidden);
        
        const allNodes = network.body.data.nodes.get();
        const visibleNodeNames = new Set();
        allNodes.forEach(node => {
            if (connectedNodes.has(node.id)) {
                visibleNodeNames.add(GraphNodes.getNodeName(node.id));
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
        
        handleEdgeVisibilityUpdate();
    });
    
    // ============================================================================
    // EVENT HANDLERS - SPECIAL NODE SELECTIONS
    // ============================================================================
    
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
    
    // ============================================================================
    // INITIALIZATION - DEFAULT STATE
    // ============================================================================
    
    // Clear selections
    selectedNodes.clear();
    checkboxes.forEach(cb => cb.checked = false);
    searchInput.value = '';
    searchResults.textContent = '';
    
    // Set default edge type visibility
    if (edgeCheckboxes.letEdges) edgeCheckboxes.letEdges.checked = true;
    if (edgeCheckboxes.implicationEdges) edgeCheckboxes.implicationEdges.checked = true;
    if (edgeCheckboxes.cauByCauEdges) edgeCheckboxes.cauByCauEdges.checked = true;
    if (edgeCheckboxes.cauBySupEdges) edgeCheckboxes.cauBySupEdges.checked = true;
    
    // Set default edge direction
    edgeDirectionRadios.forEach(radio => {
        if (radio.value === 'both') radio.checked = true;
    });
    
    // Initialize edge direction availability based on filter mode
    updateFilterModeControls();
    
    // Initialize display and rankings
    updateSelectedDisplay();
    GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
});
