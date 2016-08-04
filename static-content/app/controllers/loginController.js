myApp.controller('usernameSectionCtrl', ['$scope', '$rootScope', function ($scope, $rootScope) {
    $scope.userName = 'Enter UserName';

    $scope.toggleChatting = function () {
        if ($rootScope.chatting) {
            $scope.logoff();
        }
        else {
            $scope.login();
        }
    };

    $scope.login = function () {
        $rootScope.chatting = true;
        $rootScope.userName = document.getElementById('name-input').value;
        localStorage.userName = $rootScope.userName;
        $rootScope.channel = DEFAULT_CHANNEL_NAME;
        $rootScope.$emit('chatting');
        //document.getElementById('name-input').disabled = true;
        document.getElementById('chat-toggle').value = "Stop Chatting";
    };

    $scope.logoff = function () {
        document.getElementById('chat-toggle').value = "Start Chatting";
        //document.getElementById('name-input').disabled = false;
        $rootScope.chatting = false;
        localStorage.removeItem('userName');
        $rootScope.$emit('not chatting');
    };

    if (localStorage.getItem('userName') !== null) {
        document.getElementById('name-input').value = localStorage.userName;
        $scope.toggleChatting();
    }
}]);
