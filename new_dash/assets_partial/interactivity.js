/*
 * Non-minified clientside helpers, mirroring the real app's assets JS.
 * Registered under window.dash_clientside.tools and used by
 * ClientsideFunction-based callbacks.
 */

window.dash_clientside = window.dash_clientside || {};

window.dash_clientside.tools = {
    /**
     * Summarise a large tool-result store entirely in the browser.
     * This is the "highlighting"-style interactivity: the large payload
     * never travels back to the server.
     */
    summarizeToolResult: function (toolData) {
        if (!toolData || !toolData.x || toolData.x.length === 0) {
            return "no data yet";
        }

        var count = toolData.x.length;
        var sum = 0;
        for (var i = 0; i < count; i++) {
            sum += toolData.y[i];
        }
        var mean = sum / count;

        return count.toLocaleString() + " points, mean y = " + mean.toFixed(4);
    },

    /**
     * Track which tabs have been visited, stored in a small UI-state store.
     */
    markTabVisited: function (activeTab, visited) {
        visited = visited || {};
        if (activeTab && !visited[activeTab]) {
            var updated = Object.assign({}, visited);
            updated[activeTab] = true;
            return updated;
        }
        return window.dash_clientside.no_update;
    }
};
