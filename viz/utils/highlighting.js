/**
 * Node Highlighting Logic
 * Handles the main highlighting logic for both partition and node filtering
 */

var GraphHighlighting = (function() {
    'use strict';
    
    function highlightNodes(network, selectedPartitions, selectedNodes, partitions, filterModeRadios, edgeDirectionRadios, isEdgeHidden, searchResults, checkboxes, updateRankingsCallback, showIsolatedNodes) {
        // If partitions are selected, let partition filter handle visibility
        if (selectedPartitions.size > 0) {
            var filterMode = GraphFilters.getSelectedFilterMode(filterModeRadios);
            var edgeDirection = GraphFilters.getSelectedEdgeDirection(edgeDirectionRadios);
            var result = GraphPartitions.applyPartitionFilterWithMode(
                network, selectedPartitions, partitions, filterMode, edgeDirection, isEdgeHidden
            );
            
            GraphUIState.updateSearchResults(searchResults, result, selectedNodes, selectedPartitions);
            updateRankingsCallback();
            GraphSCC.refreshSccs(network, sccs);
            return;
        }
        
        if (selectedNodes.size === 0) {
            network.selectNodes([]);
            searchResults.textContent = '';
            GraphFilters.updateEdgeVisibility(network, selectedNodes, isEdgeHidden, function() {}, showIsolatedNodes);
            updateRankingsCallback();
            GraphSCC.refreshSccs(network, sccs);
            return;
        }
        
        var matchingIds = GraphNodes.findMatchingNodeIds(network, selectedNodes);
        
        if (matchingIds.size === 0) {
            searchResults.textContent = 'No matching nodes found';
            searchResults.style.color = '#e74c3c';
            return;
        }
        
        var filterMode = GraphFilters.getSelectedFilterMode(filterModeRadios);
        var result;
        
        if (filterMode === 'exclude') {
            result = GraphFilters.applyExcludeMode(network, matchingIds, isEdgeHidden, showIsolatedNodes);
            result.mode = 'exclude';
        } else {
            var edgeDirection = GraphFilters.getSelectedEdgeDirection(edgeDirectionRadios);
            
            // If multiple nodes selected, show only common edges (edges between selected nodes)
            // If single node selected, show neighbors as usual
            if (matchingIds.size > 1) {
                result = GraphFilters.applyCommonEdgesMode(network, matchingIds, isEdgeHidden);
                result.mode = 'include';
            } else {
                var connectedNodeIds = GraphFilters.buildNeighborhoodFromEdges(network, matchingIds, edgeDirection, isEdgeHidden);
                result = GraphFilters.applyIncludeMode(network, matchingIds, connectedNodeIds, edgeDirection, isEdgeHidden);
                result.mode = 'include';
            }
        }
        
        GraphUIState.updateSearchResults(searchResults, result, selectedNodes, selectedPartitions);
        updateRankingsCallback();
        GraphSCC.refreshSccs(network, sccs);
    }
    
    return {
        highlightNodes: highlightNodes
    };
})();
