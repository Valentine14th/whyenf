/**
 * UI State Management
 * Manages the state and display of UI controls, selected nodes and partitions
 */

var GraphUIState = (function() {
    'use strict';
    
    function updateFilterModeControls(filterModeRadios, edgeDirectionRadios) {
        var filterMode = GraphFilters.getSelectedFilterMode(filterModeRadios);
        var isExcludeMode = filterMode === 'exclude';
        
        edgeDirectionRadios.forEach(function(radio) {
            radio.disabled = isExcludeMode;
            if (radio.parentElement) {
                radio.parentElement.style.opacity = isExcludeMode ? '0.5' : '1';
                radio.parentElement.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        });
        
        // Also disable leaf/source node selection checkboxes in exclude mode
        var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
        var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
        
        if (selectLeafNodesCheckbox) {
            selectLeafNodesCheckbox.disabled = isExcludeMode;
            var leafLabel = selectLeafNodesCheckbox.parentElement;
            if (leafLabel) {
                leafLabel.style.opacity = isExcludeMode ? '0.5' : '1';
                leafLabel.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        }
        
        if (selectSourceNodesCheckbox) {
            selectSourceNodesCheckbox.disabled = isExcludeMode;
            var sourceLabel = selectSourceNodesCheckbox.parentElement;
            if (sourceLabel) {
                sourceLabel.style.opacity = isExcludeMode ? '0.5' : '1';
                sourceLabel.style.cursor = isExcludeMode ? 'not-allowed' : 'pointer';
            }
        }
    }
    
    function updatePartitionModeControls(selectedPartitions, selectedNodes, edgeCheckboxes, searchInput, checkboxes, checkboxItems, partitionSearchInput, partitionCheckboxes, partitionItems) {
        var hasPartitionsSelected = selectedPartitions.size > 0;
        var hasNodesSelected = selectedNodes.size > 0;
        
        // Disable/enable edge type controls when partitions are selected
        Object.values(edgeCheckboxes).forEach(function(checkbox) {
            if (checkbox) {
                checkbox.disabled = hasPartitionsSelected;
                if (hasPartitionsSelected) {
                    checkbox.checked = true; // Show all edge types
                }
                var label = checkbox.parentElement;
                if (label) {
                    label.style.opacity = hasPartitionsSelected ? '0.5' : '1';
                    label.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'pointer';
                }
            }
        });
        
        // Disable/enable node filtering controls when partitions are selected
        var selectionControls = document.getElementById('selection-controls');
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
        checkboxes.forEach(function(cb) {
            cb.disabled = hasPartitionsSelected;
        });
        
        // Disable/enable dropdown items when partitions are selected
        checkboxItems.forEach(function(item) {
            item.style.opacity = hasPartitionsSelected ? '0.5' : '1';
            item.style.pointerEvents = hasPartitionsSelected ? 'none' : 'auto';
        });
        
        // Disable/enable leaf/source node selection when partitions are selected
        var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
        var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
        
        if (selectLeafNodesCheckbox) {
            selectLeafNodesCheckbox.disabled = hasPartitionsSelected;
            var leafLabel = selectLeafNodesCheckbox.parentElement;
            if (leafLabel) {
                leafLabel.style.opacity = hasPartitionsSelected ? '0.5' : '1';
                leafLabel.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'pointer';
            }
        }
        
        if (selectSourceNodesCheckbox) {
            selectSourceNodesCheckbox.disabled = hasPartitionsSelected;
            var sourceLabel = selectSourceNodesCheckbox.parentElement;
            if (sourceLabel) {
                sourceLabel.style.opacity = hasPartitionsSelected ? '0.5' : '1';
                sourceLabel.style.cursor = hasPartitionsSelected ? 'not-allowed' : 'pointer';
            }
        }
        
        // Disable/enable partition filtering controls when nodes are selected
        var partitionControls = document.getElementById('partition-controls');
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
        partitionCheckboxes.forEach(function(cb) {
            cb.disabled = hasNodesSelected;
        });
        
        // Disable/enable partition items when nodes are selected
        partitionItems.forEach(function(item) {
            item.style.opacity = hasNodesSelected ? '0.5' : '1';
            item.style.pointerEvents = hasNodesSelected ? 'none' : 'auto';
        });
    }
    
    function updateSelectedNodesDisplay(selectedNodesDiv, selectedNodes, checkboxes, updateCallback, highlightCallback) {
        selectedNodesDiv.innerHTML = '';
        
        if (selectedNodes.size === 0) {
            selectedNodesDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No nodes selected</div>';
        } else {
            selectedNodes.forEach(function(nodeId) {
                var displayName = GraphNodes.getNodeDisplayName(nodeId);
                
                var tag = document.createElement('span');
                tag.className = 'selected-tag';
                tag.textContent = displayName;
                tag.onclick = function() {
                    selectedNodes.delete(nodeId);
                    checkboxes.forEach(function(cb) {
                        if (cb.value === nodeId) cb.checked = false;
                    });
                    updateCallback();
                    highlightCallback();
                };
                selectedNodesDiv.appendChild(tag);
            });
        }
    }
    
    function updateSelectedPartitionsDisplay(selectedPartitionsDiv, selectedPartitions, partitions, partitionLabels, partitionCheckboxes, updateCallback, highlightCallback) {
        selectedPartitionsDiv.innerHTML = '';
        
        if (selectedPartitions.size === 0) {
            selectedPartitionsDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No partitions selected</div>';
        } else {
            selectedPartitions.forEach(function(partitionId) {
                var numNodes = partitions[partitionId] ? partitions[partitionId].length : 0;
                var label = partitionLabels[partitionId] || 'Partition ' + partitionId;
                var tag = document.createElement('span');
                tag.className = 'selected-tag';
                tag.style.backgroundColor = '#2980b9';
                tag.textContent = label + ' (' + numNodes + ')';
                tag.onclick = function() {
                    selectedPartitions.delete(partitionId);
                    partitionCheckboxes.forEach(function(cb) {
                        if (cb.value === partitionId) cb.checked = false;
                    });
                    updateCallback();
                    highlightCallback();
                };
                selectedPartitionsDiv.appendChild(tag);
            });
        }
    }
    
    function updateSearchResults(searchResults, result, selectedNodes, selectedPartitions) {
        if (selectedPartitions.size > 0) {
            if (result.mode === 'exclude') {
                searchResults.textContent = 'Excluded ' + result.excludedCount + ' node' + (result.excludedCount !== 1 ? 's' : '') + 
                    ' in ' + selectedPartitions.size + ' partition' + (selectedPartitions.size !== 1 ? 's' : '') + 
                    ' (showing ' + result.visibleCount + ')';
            } else {
                searchResults.textContent = 'Showing ' + result.selectedCount + ' node' + (result.selectedCount !== 1 ? 's' : '') + 
                    ' in ' + selectedPartitions.size + ' partition' + (selectedPartitions.size !== 1 ? 's' : '') + 
                    ' with ' + result.neighborCount + ' neighbor' + (result.neighborCount !== 1 ? 's' : '');
            }
            searchResults.style.color = '#2980b9';
        } else if (selectedNodes.size > 0) {
            if (result.mode === 'exclude') {
                searchResults.textContent = 'Excluded ' + result.excludedCount + ' node' + (result.excludedCount > 1 ? 's' : '') + 
                    ' (showing ' + result.visibleCount + ')';
                searchResults.style.color = '#2c3e50';
            } else {
                searchResults.textContent = 'Showing ' + result.selectedCount + ' selected node' + (result.selectedCount > 1 ? 's' : '') + 
                    ' with ' + result.neighborCount + ' neighbor' + (result.neighborCount !== 1 ? 's' : '');
                searchResults.style.color = '#27ae60';
            }
        }
    }
    
    function setupClearButtonHandler(btnClear, selectedNodes, selectedPartitions, checkboxes, partitionCheckboxes, updateCallback, searchResults, searchInput, checkboxItems, handleEdgeVisibilityCallback) {
        btnClear.addEventListener('click', function() {
            selectedNodes.clear();
            selectedPartitions.clear();
            checkboxes.forEach(function(cb) { cb.checked = false; });
            partitionCheckboxes.forEach(function(cb) { cb.checked = false; });
            
            // Uncheck special selection checkboxes
            var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
            var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
            if (selectLeafNodesCheckbox) selectLeafNodesCheckbox.checked = false;
            if (selectSourceNodesCheckbox) selectSourceNodesCheckbox.checked = false;
            
            updateCallback();
            network.selectNodes([]);
            searchResults.textContent = '';
            searchInput.value = '';
            checkboxItems.forEach(function(item) { item.style.display = 'flex'; });
            
            handleEdgeVisibilityCallback();
        });
    }
    
    function setupToggleButtonHandler(toggleBtn, searchContent) {
        toggleBtn.addEventListener('click', function() {
            if (searchContent.classList.contains('hidden')) {
                searchContent.classList.remove('hidden');
                toggleBtn.textContent = 'Hide';
            } else {
                searchContent.classList.add('hidden');
                toggleBtn.textContent = 'Show';
            }
        });
    }
    
    return {
        updateFilterModeControls: updateFilterModeControls,
        updatePartitionModeControls: updatePartitionModeControls,
        updateSelectedNodesDisplay: updateSelectedNodesDisplay,
        updateSelectedPartitionsDisplay: updateSelectedPartitionsDisplay,
        updateSearchResults: updateSearchResults,
        setupClearButtonHandler: setupClearButtonHandler,
        setupToggleButtonHandler: setupToggleButtonHandler
    };
})();
