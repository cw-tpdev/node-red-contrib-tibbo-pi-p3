module.exports = function (RED) {
    "use strict";

    // #10 Medium-power 5V supply, 12V input

    var TpCommon = require('./tpCommon');

    function TP_10_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp10_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#10 out", TP_10_OutNode);
}
