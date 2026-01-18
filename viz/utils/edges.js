/**
 * Edge classification and visibility utilities
 */

const GraphEdges = (function() {
    function isEdgeHiddenByTypeFilter(edge, checkboxes) {
        // Check monotonicity filtering
        if (edge.monotonicity_type === 'monotonic' && checkboxes.monotonicEdges && !checkboxes.monotonicEdges.checked) return true;
        if (edge.monotonicity_type === 'antimonotonic' && checkboxes.antimonotonicEdges && !checkboxes.antimonotonicEdges.checked) return true;
        if (edge.monotonicity_type === 'mixed' && checkboxes.mixedEdges && !checkboxes.mixedEdges.checked) return true;
        
        return false;
    }

    function handleEdgeVisibilityUpdate(network, selectedPartitions, selectedNodes, partitions, isEdgeHidden, highlightCallback, filterDropdownCallback, updateRankingsCallback) {
        // If partitions are selected, apply partition filter first
        if (selectedPartitions.size > 0) {
            GraphPartitions.applyPartitionFilter(network, selectedPartitions, partitions, isEdgeHidden);
        }
        
        GraphFilters.updateEdgeVisibility(network, selectedNodes, isEdgeHidden, highlightCallback);
        updateRankingsCallback();
    }
    
    function setupEdgeTypeHandlers(edgeCheckboxes, handleEdgeVisibilityUpdateCallback) {
        Object.values(edgeCheckboxes).forEach(checkbox => {
            if (checkbox) checkbox.addEventListener('change', handleEdgeVisibilityUpdateCallback);
        });
    }

    return {
        isEdgeHiddenByTypeFilter,
        handleEdgeVisibilityUpdate,
        setupEdgeTypeHandlers
    };
})();
