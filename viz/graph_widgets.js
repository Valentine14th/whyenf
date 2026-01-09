document.addEventListener('DOMContentLoaded', function() {
    // ============================================================================
    // DOM ELEMENT REFERENCES
    // ============================================================================
    
    // Search and selection elements
    const searchInput = document.getElementById('search-input');
    const dropdownList = document.getElementById('dropdown-list');
    const selectedNodesDiv = document.getElementById('selected-nodes');
    const selectedPartitionsDiv = document.getElementById('selected-partitions');
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
    
    // Partition controls
    const partitionList = document.getElementById('partition-list');
    const partitionSearchInput = document.getElementById('partition-search-input');
    const partitionCheckboxes = partitionList ? partitionList.querySelectorAll('.partition-checkbox') : [];
    const partitionItems = partitionList ? partitionList.querySelectorAll('.checkbox-item') : [];
    
    // State
    let selectedNodes = new Set();
    let selectedPartitions = new Set();
    
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
        // If partitions are selected, apply partition filter first
        if (selectedPartitions.size > 0) {
            GraphPartitions.applyPartitionFilter(network, selectedPartitions, partitions, isEdgeHidden);
        }
        
        const connectedNodes = GraphFilters.updateEdgeVisibility(network, selectedNodes, isEdgeHidden, highlightNodes);
        filterDropdownByVisibility(connectedNodes);
        GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
    }
    
    function highlightNodes() {
        // If partitions are selected, let partition filter handle visibility
        if (selectedPartitions.size > 0) {
            const filterMode = GraphFilters.getSelectedFilterMode(filterModeRadios);
            const edgeDirection = GraphFilters.getSelectedEdgeDirection(edgeDirectionRadios);
            const result = GraphPartitions.applyPartitionFilterWithMode(
                network, selectedPartitions, partitions, filterMode, edgeDirection, isEdgeHidden
            );
            
            if (result.mode === 'exclude') {
                searchResults.textContent = `Excluded ${result.excludedCount} node${result.excludedCount !== 1 ? 's' : ''} in ${selectedPartitions.size} partition${selectedPartitions.size !== 1 ? 's' : ''} (showing ${result.visibleCount})`;
            } else {
                searchResults.textContent = `Showing ${result.selectedCount} node${result.selectedCount !== 1 ? 's' : ''} in ${selectedPartitions.size} partition${selectedPartitions.size !== 1 ? 's' : ''} with ${result.neighborCount} neighbor${result.neighborCount !== 1 ? 's' : ''}`;
            }
            searchResults.style.color = '#2980b9';
            GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
            return;
        }
        
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
        // Update selected nodes display
        selectedNodesDiv.innerHTML = '';
        
        if (selectedNodes.size === 0) {
            selectedNodesDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No nodes selected</div>';
        } else {
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
        
        // Update selected partitions display
        selectedPartitionsDiv.innerHTML = '';
        
        if (selectedPartitions.size === 0) {
            selectedPartitionsDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No partitions selected</div>';
        } else {
            selectedPartitions.forEach(partitionId => {
                const numNodes = partitions[partitionId] ? partitions[partitionId].length : 0;
                const label = partitionLabels[partitionId] || `Partition ${partitionId}`;
                const tag = document.createElement('span');
                tag.className = 'selected-tag';
                tag.style.backgroundColor = '#2980b9';
                tag.textContent = `${label} (${numNodes})`;
                tag.onclick = () => {
                    selectedPartitions.delete(partitionId);
                    partitionCheckboxes.forEach(cb => {
                        if (cb.value === partitionId) cb.checked = false;
                    });
                    updateSelectedDisplay();
                    highlightNodes();
                };
                selectedPartitionsDiv.appendChild(tag);
            });
        }
        
        // Update control states based on partition selection
        updatePartitionModeControls();
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
    
    function updatePartitionModeControls() {
        const hasPartitionsSelected = selectedPartitions.size > 0;
        const hasNodesSelected = selectedNodes.size > 0;
        
        // Disable/enable edge type controls when partitions are selected
        Object.values(edgeCheckboxes).forEach(checkbox => {
            if (checkbox) {
                checkbox.disabled = hasPartitionsSelected;
                if (hasPartitionsSelected) {
                    checkbox.checked = true; // Show all edge types
                }
                const label = checkbox.parentElement;
                if (label) {
                    label.style.opacity = hasPartitionsSelected ? '0.5' : '1';
                    label.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'pointer';
                }
            }
        });
        
        // Disable/enable node filtering controls when partitions are selected
        const selectionControls = document.getElementById('selection-controls');
        if (selectionControls) {
            selectionControls.style.opacity = hasPartitionsSelected ? '0.5' : '1';
            selectionControls.style.pointerEvents = hasPartitionsSelected ? 'none' : 'auto';
        }
        
        // Disable/enable search input when partitions are selected
        if (searchInput) {
            searchInput.disabled = hasPartitionsSelected;
            searchInput.style.opacity = hasPartitionsSelected ? '0.5' : '1';
            searchInput.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'text';
        }
        
        // Disable/enable node checkboxes when partitions are selected
        checkboxes.forEach(cb => {
            cb.disabled = hasPartitionsSelected;
        });
        
        // Disable/enable dropdown items when partitions are selected
        checkboxItems.forEach(item => {
            item.style.opacity = hasPartitionsSelected ? '0.5' : '1';
            item.style.pointerEvents = hasPartitionsSelected ? 'none' : 'auto';
        });
        
        // Disable/enable leaf/source node selection when partitions are selected
        const selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
        const selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
        
        if (selectLeafNodesCheckbox) {
            selectLeafNodesCheckbox.disabled = hasPartitionsSelected;
            const leafLabel = selectLeafNodesCheckbox.parentElement;
            if (leafLabel) {
                leafLabel.style.opacity = hasPartitionsSelected ? '0.5' : '1';
                leafLabel.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'pointer';
            }
        }
        
        if (selectSourceNodesCheckbox) {
            selectSourceNodesCheckbox.disabled = hasPartitionsSelected;
            const sourceLabel = selectSourceNodesCheckbox.parentElement;
            if (sourceLabel) {
                sourceLabel.style.opacity = hasPartitionsSelected ? '0.5' : '1';
                sourceLabel.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'pointer';
            }
        }
        
        // Disable/enable partition filtering controls when nodes are selected
        const partitionControls = document.getElementById('partition-controls');
        if (partitionControls) {
            partitionControls.style.opacity = hasNodesSelected ? '0.5' : '1';
            partitionControls.style.pointerEvents = hasNodesSelected ? 'none' : 'auto';
        }
        
        // Disable/enable partition search input when nodes are selected
        if (partitionSearchInput) {
            partitionSearchInput.disabled = hasNodesSelected;
            partitionSearchInput.style.opacity = hasNodesSelected ? '0.5' : '1';
            partitionSearchInput.style.cursor = hasNodesSelected ? 'not-allowed' : 'text';
        }
        
        // Disable/enable partition checkboxes when nodes are selected
        partitionCheckboxes.forEach(cb => {
            cb.disabled = hasNodesSelected;
        });
        
        // Disable/enable partition items when nodes are selected
        partitionItems.forEach(item => {
            item.style.opacity = hasNodesSelected ? '0.5' : '1';
            item.style.pointerEvents = hasNodesSelected ? 'none' : 'auto';
        });
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
            if (selectedNodes.size > 0 || selectedPartitions.size > 0) highlightNodes();
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
    
    if (partitionSearchInput) {
        partitionSearchInput.addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            partitionItems.forEach(item => {
                const label = item.querySelector('label').textContent.toLowerCase();
                item.style.display = label.includes(filter) ? 'flex' : 'none';
            });
        });
    }
    
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
        selectedPartitions.clear();
        checkboxes.forEach(cb => cb.checked = false);
        partitionCheckboxes.forEach(cb => cb.checked = false);
        
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
    // EVENT HANDLERS - PARTITION FILTERING
    // ============================================================================
    
    partitionCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                selectedPartitions.add(this.value);
            } else {
                selectedPartitions.delete(this.value);
            }
            updateSelectedDisplay();
            highlightNodes();
        });
    });
    
    // Make clicking on partition item also toggle checkbox
    partitionItems.forEach(item => {
        item.addEventListener('click', function(e) {
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
                const checkbox = this.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    });
    
    // ============================================================================
    // EVENT HANDLERS - SCC CONTROLS
    // ============================================================================

    const sccToggle = document.getElementById('scc-toggle');

    if (sccToggle && typeof sccs !== 'undefined' && sccs.length > 0) {
        sccToggle.addEventListener('change', function() {
            GraphSCC.toggleSccs(network, sccs, sccToggle);
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
    
    // Clear all selections
    selectedNodes.clear();
    selectedPartitions.clear();
    checkboxes.forEach(cb => cb.checked = false);
    partitionCheckboxes.forEach(cb => cb.checked = false);
    searchInput.value = '';
    if (partitionSearchInput) partitionSearchInput.value = '';
    searchResults.textContent = '';
    
    // Clear leaf/source node selections (variables already declared above)
    if (selectLeafNodesCheckbox) selectLeafNodesCheckbox.checked = false;
    if (selectSourceNodesCheckbox) selectSourceNodesCheckbox.checked = false;
    
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
