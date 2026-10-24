package com.easymeals.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.*
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.ui.screens.*
import com.easymeals.app.ui.theme.EasyMealsTheme
import com.easymeals.app.ui.theme.ForestGreen

enum class AppTab(val title: String, val icon: ImageVector) {
    TODAY("Hôm nay", Icons.Default.DinnerDining),
    PANTRY("Tủ lạnh", Icons.Default.Kitchen),
    SHOPPING("Đi chợ", Icons.Default.ShoppingCart),
    RECIPES("Công thức", Icons.Default.MenuBook),
    SETTINGS("Cài đặt", Icons.Default.Settings)
}

class MainActivity : ComponentActivity() {

    private lateinit var repository: AppRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        repository = AppRepository(applicationContext)

        setContent {
            EasyMealsTheme {
                MainContent(repository = repository)
            }
        }
    }
}

@Composable
fun MainContent(repository: AppRepository) {
    var selectedTab by remember { mutableStateOf(AppTab.TODAY) }
    val undoMessage by repository.undoMessage.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(undoMessage) {
        val msg = undoMessage
        if (msg != null) {
            val result = snackbarHostState.showSnackbar(
                message = msg,
                actionLabel = "Hoàn tác",
                duration = SnackbarDuration.Short
            )
            if (result == SnackbarResult.ActionPerformed) {
                repository.undoLastEatMeal()
            }
            repository.clearUndoMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            NavigationBar(
                tonalElevation = 8.dp
            ) {
                AppTab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = selectedTab == tab,
                        onClick = { selectedTab = tab },
                        icon = { Icon(tab.icon, contentDescription = tab.title) },
                        label = { Text(tab.title) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = ForestGreen,
                            selectedTextColor = ForestGreen,
                            indicatorColor = ForestGreen.copy(alpha = 0.15f)
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                AppTab.TODAY -> TodayScreen(repository)
                AppTab.PANTRY -> PantryScreen(repository)
                AppTab.SHOPPING -> ShoppingScreen(repository)
                AppTab.RECIPES -> RecipesScreen(repository)
                AppTab.SETTINGS -> SettingsScreen(repository)
            }
        }
    }
}
