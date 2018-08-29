module.exports = function (RED) {
    "use strict";

    // #06 Two high-power relays

    var TpCommon = require('./tpCommon');

    function TP_06_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp06_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#06 out", TP_06_OutNode);
}
