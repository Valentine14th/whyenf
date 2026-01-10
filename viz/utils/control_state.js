/**
 * Control State Management
 * Manages the enabled/disabled state of various UI controls based on filtering mode
 */

var GraphControlState = (function() {
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
    
    return {
        updateFilterModeControls: updateFilterModeControls,
        updatePartitionModeControls: updatePartitionModeControls
    };
})();
