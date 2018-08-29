module.exports = function (RED) {
    "use strict";

    // #09 Low-power 5V supply, 12V input

    var TpCommon = require('./tpCommon');

    function TP_09_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp09_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#09 out", TP_09_OutNode);
}
