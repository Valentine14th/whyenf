/**
 * UI State Management
 * Manages the state and display of selected nodes and partitions
 */

var GraphUIState = (function() {
    'use strict';
    
    function updateSelectedNodesDisplay(selectedNodesDiv, selectedNodes, checkboxes, updateCallback, highlightCallback) {
        selectedNodesDiv.innerHTML = '';
        
        if (selectedNodes.size === 0) {
            selectedNodesDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No nodes selected</div>';
        } else {
            selectedNodes.forEach(function(nodeName) {
                var tag = document.createElement('span');
                tag.className = 'selected-tag';
                tag.textContent = nodeName;
                tag.onclick = function() {
                    selectedNodes.delete(nodeName);
                    checkboxes.forEach(function(cb) {
                        if (cb.value === nodeName) cb.checked = false;
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
    
    return {
        updateSelectedNodesDisplay: updateSelectedNodesDisplay,
        updateSelectedPartitionsDisplay: updateSelectedPartitionsDisplay,
        updateSearchResults: updateSearchResults
    };
})();
