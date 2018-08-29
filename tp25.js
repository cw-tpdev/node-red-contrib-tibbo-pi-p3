module.exports = function (RED) {
    "use strict";

    // #25 High-power 5V supply, 12/24/48V input

    var TpCommon = require('./tpCommon');

    function TP_25_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp25_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#25 out", TP_25_OutNode);
}
