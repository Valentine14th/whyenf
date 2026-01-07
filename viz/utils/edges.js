/**
 * Edge classification and visibility utilities
 */

const GraphEdges = (function() {
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

    function getEdgeTypeVisibilitySettings(checkboxes) {
        return {
            showLetEdges: checkboxes.letEdges ? checkboxes.letEdges.checked : true,
            showImplicationEdges: checkboxes.implicationEdges ? checkboxes.implicationEdges.checked : true,
            showCauByCauEdges: checkboxes.cauByCauEdges ? checkboxes.cauByCauEdges.checked : true,
            showCauBySupEdges: checkboxes.cauBySupEdges ? checkboxes.cauBySupEdges.checked : true
        };
    }

    function isEdgeHiddenByTypeFilter(edge, checkboxes) {
        const settings = getEdgeTypeVisibilitySettings(checkboxes);
        const { isLetEdge, isImplicationEdge, isCauByCauEdge, isCauBySupEdge, isMixedCausalityEdge } = classifyEdge(edge);
        
        if (isLetEdge && !settings.showLetEdges) return true;
        if (isImplicationEdge && !settings.showImplicationEdges) return true;
        if (isCauByCauEdge && !settings.showCauByCauEdges) return true;
        if (isCauBySupEdge && !settings.showCauBySupEdges) return true;
        if (isMixedCausalityEdge && (!settings.showCauByCauEdges || !settings.showCauBySupEdges)) return true;
        
        return false;
    }

    return {
        EdgeColors,
        getEdgeColor,
        classifyEdge,
        getEdgeTypeVisibilitySettings,
        isEdgeHiddenByTypeFilter
    };
})();
